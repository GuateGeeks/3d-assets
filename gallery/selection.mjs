export function chooseInitialModel(models, {requestedId, preferredId, eligibleIds}) {
  const requested = models.find(model => model.id === requestedId);
  if (requested) return requested;
  const eligible = new Set(eligibleIds);
  return models.find(model => model.id === preferredId && eligible.has(model.id))
    || eligibleIds.map(id => models.find(model => model.id === id)).find(Boolean) || null;
}

export function chooseDisplayVariant(model, variants) {
  return variants.find(variant => variant.id === model.id
    && variant.sourceFile === model.file && variant.sourceSha256 === model.sha256
    && variant.qa?.technical === 'PASS' && variant.qa?.visual === 'PASS'
    && /^gallery\/compat\/models\/[a-z0-9-]+\.glb$/.test(variant.file)) || null;
}
