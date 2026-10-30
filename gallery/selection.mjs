export function chooseInitialModel(models, {requestedId, preferredId, eligibleIds}) {
  const requested = models.find(model => model.id === requestedId);
  if (requested) return requested;
  const eligible = new Set(eligibleIds);
  return models.find(model => model.id === preferredId && eligible.has(model.id))
    || eligibleIds.map(id => models.find(model => model.id === id)).find(Boolean) || null;
}
