"""Optional local CLIP search. No AI packages are imported at module scope."""
import json
import sqlite3
import sys
from pathlib import Path


class Search:
    def __init__(self, cache):
        from croweyes_extensions import load_optional, root
        self.np=load_optional('semantic','numpy')
        ort=load_optional('semantic','onnxruntime')
        tokenizer=load_optional('semantic','tokenizers')
        base=root()/'semantic/models/clip' if getattr(sys,'frozen',False) else Path(__file__).resolve().parent/'.optional-vendor/semantic/models/clip'
        options=ort.SessionOptions()
        options.intra_op_num_threads=2
        options.inter_op_num_threads=1
        self.vision=ort.InferenceSession(str(base/'onnx/vision_model_quantized.onnx'),options,providers=['CPUExecutionProvider'])
        self.text=ort.InferenceSession(str(base/'onnx/text_model_quantized.onnx'),options,providers=['CPUExecutionProvider'])
        self.tokenizer=tokenizer.Tokenizer.from_file(str(base/'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=77)
        self.config=json.loads((base/'preprocessor_config.json').read_text())
        self.cache=Path(cache)
        self.cache.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.cache) as db:
            db.execute('CREATE TABLE IF NOT EXISTS embeddings(path TEXT PRIMARY KEY, fingerprint TEXT, vector TEXT)')

    def normalize(self, vector):
        vector=self.np.asarray(vector,dtype='float32').reshape(-1)
        return vector/max(1e-12,float(self.np.linalg.norm(vector)))

    def image_vector(self,image):
        from PIL import Image,ImageOps
        np=self.np
        size=self.config['crop_size']['height']
        image=ImageOps.fit(image.convert('RGB'),(size,size),method=Image.Resampling.BICUBIC)
        pixels=np.asarray(image,dtype='float32')/255
        pixels=(pixels-np.array(self.config['image_mean'],dtype='float32'))/np.array(self.config['image_std'],dtype='float32')
        tensor=np.transpose(pixels,(2,0,1))[None,...]
        names=[item.name for item in self.vision.get_outputs()]
        name='image_embeds' if 'image_embeds' in names else names[-1]
        return self.normalize(self.vision.run([name],{'pixel_values':tensor})[0])

    def query(self,query,paths,cancel,progress):
        from croweyes_workflows import open_image
        np=self.np
        encoded=self.tokenizer.encode(query)
        ids=np.asarray([encoded.ids],dtype='int64')
        mask=np.ones_like(ids)
        feed={item.name:ids if item.name=='input_ids' else mask for item in self.text.get_inputs()}
        names=[item.name for item in self.text.get_outputs()]
        name='text_embeds' if 'text_embeds' in names else names[-1]
        vector=self.normalize(self.text.run([name],feed)[0])
        results=[]
        errors=[]
        with sqlite3.connect(self.cache) as db:
            for i,path in enumerate(paths):
                if cancel.is_set():break
                try:
                    path=Path(path).resolve()
                    stat=path.stat()
                    fingerprint=f'{stat.st_size}:{stat.st_mtime_ns}'
                    row=db.execute('SELECT fingerprint,vector FROM embeddings WHERE path=?',(str(path),)).fetchone()
                    if row and row[0]==fingerprint:
                        image_vector=np.asarray(json.loads(row[1]),dtype='float32')
                    else:
                        image_vector=self.image_vector(open_image(path,preview=True))
                        db.execute('INSERT OR REPLACE INTO embeddings VALUES(?,?,?)',(str(path),fingerprint,json.dumps(image_vector.tolist())))
                        db.commit()
                    results.append((float(np.dot(vector,image_vector)),str(path)))
                except Exception as exc:
                    errors.append(str(path)+': '+str(exc))
                progress(i+1,len(paths))
        return sorted(results,reverse=True)[:30],errors
