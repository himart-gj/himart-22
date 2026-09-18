const fs = require('fs');
let content = fs.readFileSync('src/components/PopCard.tsx', 'utf8');

content = content.replace('{/* Total Summary Ribbon */}', '</div>\n\n      {/* Total Summary Ribbon */}');

fs.writeFileSync('src/components/PopCard.tsx', content);
