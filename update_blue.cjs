const fs = require('fs');
let content = fs.readFileSync('src/components/PopCard.tsx', 'utf8');

content = content.replace(/text-blue-900/g, 'text-indigo-950');
content = content.replace(/text-blue-700/g, 'text-indigo-700');
content = content.replace(/bg-blue-600/g, 'bg-indigo-600');
content = content.replace(/text-blue-600/g, 'text-indigo-600');
content = content.replace(/bg-blue-500/g, 'bg-indigo-500');
content = content.replace(/bg-blue-50/g, 'bg-indigo-50/70');

fs.writeFileSync('src/components/PopCard.tsx', content);
