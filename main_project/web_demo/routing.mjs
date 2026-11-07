// A bounded browser demonstration; this does not replace the Python research solver.
export function shortestPath(width, height, blocked, start, target) {
  const count = width * height;
  if (blocked.has(start) || blocked.has(target)) return null;
  const distances = new Float64Array(count).fill(Infinity);
  const previous = new Int32Array(count).fill(-1);
  const visited = new Uint8Array(count);
  distances[start] = 0;
  for (let iteration = 0; iteration < count; iteration++) {
    let current = -1, best = Infinity;
    for (let i = 0; i < count; i++) if (!visited[i] && distances[i] < best) { current = i; best = distances[i]; }
    if (current < 0) return null;
    if (current === target) {
      const path = []; let cell = current;
      while (cell >= 0) { path.push(cell); cell = previous[cell]; }
      return { path: path.reverse(), distance: distances[current] };
    }
    visited[current] = 1;
    const x = current % width, y = Math.floor(current / width);
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      if (!dx && !dy) continue;
      const nx = x + dx, ny = y + dy;
      if (nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
      const next = ny * width + nx;
      if (visited[next] || blocked.has(next)) continue;
      if (dx && dy && (blocked.has(y*width+nx) || blocked.has(ny*width+x))) continue;
      const proposed = best + Math.hypot(dx, dy);
      if (proposed < distances[next]) { distances[next] = proposed; previous[next] = current; }
    }
  }
  return null;
}
export function preset(name, width, height) {
  const blocked = new Set();
  if (name === 'clear') return blocked;
  for (let y = name === 'closed' ? 0 : 3; y < (name === 'closed' ? height : height-3); y++) {
    blocked.add(y * width + Math.floor(width/2));
  }
  return blocked;
}
