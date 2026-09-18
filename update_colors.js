const fs = require('fs');
let content = fs.readFileSync('src/components/PopCard.tsx', 'utf8');

// Replace dark slate with deep navy
content = content.replace(/border-slate-800/g, 'border-indigo-950');
content = content.replace(/bg-slate-800/g, 'bg-indigo-950');
content = content.replace(/text-slate-800/g, 'text-indigo-950');

// Replace yellow with richer amber
content = content.replace(/text-yellow-400/g, 'text-amber-400');
content = content.replace(/bg-yellow-700/g, 'bg-amber-600');
content = content.replace(/border-yellow-600\/30/g, 'border-amber-600/30');

// Replace lighter slate with indigo tints
content = content.replace(/border-slate-200/g, 'border-indigo-100');
content = content.replace(/bg-slate-100/g, 'bg-indigo-50');
content = content.replace(/bg-slate-50/g, 'bg-indigo-50/50');
content = content.replace(/text-slate-500/g, 'text-indigo-700/70');
content = content.replace(/text-slate-600/g, 'text-indigo-800');
content = content.replace(/text-slate-700/g, 'text-indigo-900');
content = content.replace(/text-slate-400/g, 'text-indigo-300');
content = content.replace(/text-slate-300/g, 'text-indigo-200');

// Replace primary red with rose (a bit more elegant/modern)
content = content.replace(/text-red-600/g, 'text-rose-600');

// A/S Badge specific updates
content = content.replace(/bg-blue-800/g, 'bg-indigo-700');
content = content.replace(/border-blue-400/g, 'border-indigo-300');
content = content.replace(/text-blue-900/g, 'text-indigo-900');

fs.writeFileSync('src/components/PopCard.tsx', content);
