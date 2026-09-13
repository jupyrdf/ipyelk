// Validate the actual ELK output, not just the Python node definitions.
const fs = require('fs');
const ELK = require('elkjs/lib/elk.bundled.js');
const graph = JSON.parse(fs.readFileSync(0, 'utf8'));
function strip(el) {
  delete el.properties;
  for (const key of ['children', 'labels', 'ports', 'edges'])
    for (const child of el[key] || []) strip(child);
}
strip(graph);
new ELK().layout(graph).then(result => {
  const owners = new Map();
  for (const node of result.children) {
    for (const port of node.ports || []) owners.set(port.id, node);
  }
  let checked = 0;
  for (const edge of result.edges) {
    const source = owners.get(edge.sources[0]);
    const target = owners.get(edge.targets[0]);
    if (!source || !target) throw Error(`Missing port owner: ${edge.id}`);
    const section = edge.sections[0];
    for (const [actual, expected] of [
      [section.startPoint.x, source.x + source.width],
      [section.startPoint.y, source.y + source.height / 2],
      [section.endPoint.x, target.x],
      [section.endPoint.y, target.y + target.height / 2],
    ]) {
      if (Math.abs(actual - expected) > 0.01)
        throw Error(`${edge.id}: anchor ${actual}, expected ${expected}`);
    }
    checked++;
  }
  console.log(`Verified ${checked} edges: right-center to left-center.`);
}).catch(error => { console.error(error); process.exitCode = 1; });
