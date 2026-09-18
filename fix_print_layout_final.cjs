const fs = require('fs');
let app = fs.readFileSync('src/App.tsx', 'utf8');

// Use precise paddings to center around the 50.5% cutting line and maximize card size
const targetStrRegex = /\{pair\.map\(\(product, idx\) => \(\s*<div key=\{product\.id\} className="w-\[148\.5mm\] h-\[210mm\] flex items-center justify-center box-border shrink-0">\s*<div className=\{\`w-full h-full flex items-center justify-center \$\{idx === 0 \? 'print:pl-\[1mm\] print:pr-\[8mm\]' : 'print:pl-\[9mm\] print:pr-\[0mm\]'\} print:py-\[5mm\]\`\}>\s*<div className="w-full h-full">\s*<PopCard product=\{product\} cardBenefit=\{selectedCard\} \/>\s*<\/div>\s*<\/div>\s*<\/div>\s*\)\)\}/;

const replacement = `{pair.map((product, idx) => (
                    <div key={product.id} className="w-[148.5mm] h-[210mm] flex items-center justify-center box-border shrink-0">
                      <div className={\`w-full h-full flex items-center justify-center \${idx === 0 ? 'print:pl-[4mm] print:pr-[5.5mm]' : 'print:pl-[8.5mm] print:pr-[1mm]'} print:py-[6mm]\`}>
                        <div className="w-full h-full relative">
                          <PopCard product={product} cardBenefit={selectedCard} />
                        </div>
                      </div>
                    </div>
                  ))}`;

app = app.replace(targetStrRegex, replacement);

fs.writeFileSync('src/App.tsx', app);
