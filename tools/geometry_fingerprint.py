"""Conservative, rotation/translation/uniform-scale invariant triangle fingerprint for GLB.
It compares triangle edge-length distributions, including node transforms. A match
is a duplicate candidate, not proof of authorship; nonmatches can still be variants.
"""
import json,struct,math,hashlib
I=[1.,0,0,0,0,1.,0,0,0,0,1.,0,0,0,0,1.]
def document(data):
    pos=12;doc=None;binary=b''
    if data[:4]!=b'glTF':raise ValueError('Not GLB')
    while pos<len(data):
        n,t=struct.unpack_from('<II',data,pos);chunk=data[pos+8:pos+8+n];pos+=8+n
        if t==0x4e4f534a:doc=json.loads(chunk)
        elif t==0x004e4942:binary=chunk
    return doc,binary
def mul(a,b):return [sum(a[k*4+r]*b[c*4+k] for k in range(4)) for c in range(4) for r in range(4)]
def transform(n):
    if 'matrix' in n:return n['matrix']
    x,y,z,w=n.get('rotation',[0,0,0,1]);sx,sy,sz=n.get('scale',[1,1,1]);tx,ty,tz=n.get('translation',[0,0,0])
    return [(1-2*y*y-2*z*z)*sx,(2*x*y+2*z*w)*sx,(2*x*z-2*y*w)*sx,0,(2*x*y-2*z*w)*sy,(1-2*x*x-2*z*z)*sy,(2*y*z+2*x*w)*sy,0,(2*x*z+2*y*w)*sz,(2*y*z-2*x*w)*sz,(1-2*x*x-2*y*y)*sz,0,tx,ty,tz,1]
def fingerprint(data,decoded=None):
    doc,binary=document(data);triangles=[]
    def accessor(idx):
        a=doc['accessors'][idx]
        if 'sparse' in a:raise ValueError('Sparse accessor not fingerprinted')
        v=doc['bufferViews'][a['bufferView']]
        if v.get('buffer',0)!=0:raise ValueError('External buffer')
        code={5120:'b',5121:'B',5122:'h',5123:'H',5125:'I',5126:'f'}[a['componentType']]
        dim={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];fmt='<'+code*dim;size=struct.calcsize(fmt)
        offset=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',size)
        return [struct.unpack_from(fmt,binary,offset+i*stride) for i in range(a['count'])]
    def walk(idx,parent):
        node=doc['nodes'][idx];m=mul(parent,transform(node))
        if 'mesh' in node:
            for primitive_index,p in enumerate(doc['meshes'][node['mesh']]['primitives']):
                if p.get('mode',4)!=4:raise ValueError('Non-triangle primitive')
                compression=p.get('extensions',{}).get('KHR_draco_mesh_compression')
                geometry=decoded[f"{node['mesh']}:{primitive_index}"] if compression and decoded is not None else None
                if compression and geometry is None:raise ValueError('Draco geometry requires decoded comparison input')
                verts=geometry['positions'] if geometry else accessor(p['attributes']['POSITION'])
                world=[tuple(sum(m[k*4+j]*v[k] for k in range(3))+m[12+j] for j in range(3)) for v in verts]
                ix=geometry['indices'] if geometry else [v[0] for v in accessor(p['indices'])] if 'indices' in p else list(range(len(verts)))
                for k in range(0,len(ix),3):
                    a,b,c=[world[t] for t in ix[k:k+3]]
                    edges=sorted(sum((v[j]-w[j])**2 for j in range(3)) for v,w in [(a,b),(b,c),(c,a)])
                    triangles.append(edges)
        for child in node.get('children',[]):walk(child,m)
    roots=doc.get('scenes',[{}])[doc.get('scene',0)].get('nodes',[])
    for n in roots:walk(n,I)
    if not triangles:raise ValueError('No triangles')
    largest=max(t[2] for t in triangles)
    if not largest:raise ValueError('Zero geometry')
    rounded=sorted(tuple(round(e/largest*1e6) for e in t) for t in triangles)
    return {'method':'triangle-edge-distribution-v1','sha256':hashlib.sha256(json.dumps(rounded,separators=(',',':')).encode()).hexdigest(),'triangles':len(triangles)}
