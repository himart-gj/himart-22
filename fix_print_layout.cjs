const fs = require('fs');
let app = fs.readFileSync('src/App.tsx', 'utf8');

const targetStrRegex = /\{pair\.map\(\(product\) => \(\s*<div key=\{product\.id\} className="w-\[148\.5mm\] h-\[210mm\] flex items-center justify-center box-border shrink-0">\s*<div className="w-full h-full print:p-2 flex items-center justify-center">\s*<PopCard product=\{product\} cardBenefit=\{selectedCard\} \/>\s*<\/div>\s*<\/div>\s*\)\)\}/;

const replacement = `{pair.map((product, idx) => (
                    <div key={product.id} className="w-[148.5mm] h-[210mm] flex items-center justify-center box-border shrink-0">
                      <div className={\`w-full h-full flex items-center justify-center \${idx === 0 ? 'print:pl-[1mm] print:pr-[8mm]' : 'print:pl-[9mm] print:pr-[0mm]'} print:py-[5mm]\`}>
                        <div className="w-full h-full">
                          <PopCard product={product} cardBenefit={selectedCard} />
                        </div>
                      </div>
                    </div>
                  ))}`;

app = app.replace(targetStrRegex, replacement);
fs.writeFileSync('src/App.tsx', app);
