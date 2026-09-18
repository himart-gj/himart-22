const fs = require('fs');
let app = fs.readFileSync('src/App.tsx', 'utf8');

// Revert dashed line to center
app = app.replace(/<div className="absolute left-\[50\.5%\]/g, '<div className="absolute left-1/2');

// Replace the complicated padding with uniform padding
const regex = /<div className=\{\`w-full h-full flex items-center justify-center \$\{idx === 0 \? 'print:pl-\[4mm\] print:pr-\[5\.5mm\]' : 'print:pl-\[8\.5mm\] print:pr-\[1mm\]'\} print:py-\[6mm\]\`\}>/g;
app = app.replace(regex, '<div className="w-full h-full flex items-center justify-center print:p-[10mm]">');

fs.writeFileSync('src/App.tsx', app);
