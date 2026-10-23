// Decode only geometry for comparison. Native model bytes are never changed.
const fs = require('node:fs');
const path = require('node:path');
const factory = require('../gallery/vendor/draco/draco_decoder.js');
(async () => {
  const raw = fs.readFileSync(process.argv[2]);
  let doc, binary;
  for (let pos = 12; pos < raw.length;) {
    const size = raw.readUInt32LE(pos), type = raw.readUInt32LE(pos + 4);
    const chunk = raw.subarray(pos + 8, pos + 8 + size);
    if (type === 0x4e4f534a) doc = JSON.parse(chunk.toString());
    if (type === 0x004e4942) binary = chunk;
    pos += 8 + size;
  }
  const module = await factory({});
  const output = {};
  for (let mi = 0; mi < doc.meshes.length; mi++) {
    for (let pi = 0; pi < doc.meshes[mi].primitives.length; pi++) {
      const primitive = doc.meshes[mi].primitives[pi];
      const extension = primitive.extensions?.KHR_draco_mesh_compression;
      if (!extension) continue;
      const view = doc.bufferViews[extension.bufferView];
      const data = binary.subarray(view.byteOffset || 0, (view.byteOffset || 0) + view.byteLength);
      const buffer = new module.DecoderBuffer();
      buffer.Init(new Int8Array(data), data.length);
      const decoder = new module.Decoder();
      const mesh = new module.Mesh();
      const status = decoder.DecodeBufferToMesh(buffer, mesh);
      if (!status.ok() || !mesh.ptr) throw Error('Draco geometry decode failed');
      const attribute = decoder.GetAttributeByUniqueId(mesh, extension.attributes.POSITION);
      const values = new module.DracoFloat32Array();
      decoder.GetAttributeFloatForAllPoints(mesh, attribute, values);
      const positions = [];
      for (let v = 0; v < mesh.num_points(); v++) {
        positions.push([values.GetValue(v * 3), values.GetValue(v * 3 + 1), values.GetValue(v * 3 + 2)]);
      }
      const face = new module.DracoInt32Array(), indices = [];
      for (let f = 0; f < mesh.num_faces(); f++) {
        decoder.GetFaceFromMesh(mesh, f, face);
        indices.push(face.GetValue(0), face.GetValue(1), face.GetValue(2));
      }
      output[`${mi}:${pi}`] = {positions, indices};
      for (const object of [face, values, mesh, decoder, buffer]) module.destroy(object);
    }
  }
  process.stdout.write(JSON.stringify(output));
})().catch(error => { process.stderr.write(error.message + '\n'); process.exitCode = 1; });
