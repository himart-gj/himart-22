const fs = require('fs');
let content = fs.readFileSync('src/components/PopCard.tsx', 'utf8');

// Revert colors to standard high-contrast
content = content.replace(/border-indigo-950/g, 'border-slate-800');
content = content.replace(/bg-indigo-950/g, 'bg-slate-800');
content = content.replace(/text-indigo-950/g, 'text-slate-800');

content = content.replace(/text-amber-400/g, 'text-yellow-400');
content = content.replace(/bg-amber-600/g, 'bg-yellow-700');
content = content.replace(/border-amber-600\/30/g, 'border-yellow-600/30');
content = content.replace(/text-amber-900/g, 'text-yellow-800');
content = content.replace(/bg-amber-50/g, 'bg-yellow-50');
content = content.replace(/border-amber-200/g, 'border-yellow-200');

content = content.replace(/border-indigo-100/g, 'border-slate-200');
content = content.replace(/bg-indigo-50\/50/g, 'bg-slate-50');
content = content.replace(/bg-indigo-50/g, 'bg-slate-100');
content = content.replace(/text-indigo-700\/70/g, 'text-slate-500');
content = content.replace(/text-indigo-800/g, 'text-slate-600');
content = content.replace(/text-indigo-900/g, 'text-slate-700');
content = content.replace(/text-indigo-300/g, 'text-slate-400');
content = content.replace(/text-indigo-200/g, 'text-slate-300');

content = content.replace(/text-rose-600/g, 'text-red-600');

content = content.replace(/bg-indigo-700/g, 'bg-blue-800');
content = content.replace(/border-indigo-300/g, 'border-blue-400');
content = content.replace(/text-indigo-700/g, 'text-blue-700');
content = content.replace(/bg-indigo-600/g, 'bg-blue-600');
content = content.replace(/text-indigo-600/g, 'text-blue-600');
content = content.replace(/bg-indigo-500/g, 'bg-blue-500');
content = content.replace(/bg-indigo-50\/70/g, 'bg-blue-50');

// Replace badge layout
const badgeRegex = /\{\/\* 로제트 모양 뱃지 \*\/\}.*?(?=<div className="font-bold text-slate-700)/s;
const newBadge = `
            {/* 깔끔하고 큼직한 원형 뱃지 */}
            <div className="w-14 h-14 bg-blue-800 text-white rounded-full flex flex-col items-center justify-center border-2 border-dashed border-blue-400 mb-1.5 shadow-sm">
              <span className="text-2xl font-black leading-none">{warrantyYears}</span>
              <span className="text-[9px] font-bold mt-0.5">YEARS</span>
            </div>
            `;
content = content.replace(badgeRegex, newBadge);

// Also fix the text inside that box
content = content.replace(/<span className="text-slate-800 font-extrabold">\{warrantyYears\}년간 무상 A\/S<\/span>로<br\/>안심하고 사용하세요!/g, '<span className="text-blue-800 font-extrabold">{warrantyYears}년간 무상 A/S</span>로<br/>안심하고 사용하세요!');

fs.writeFileSync('src/components/PopCard.tsx', content);
