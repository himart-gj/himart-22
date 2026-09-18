import * as XLSX from 'xlsx';
import { ProductData } from '../types';

// 다양한 엑셀 헤더 이름을 유연하게 인식하기 위한 별칭(Alias) 사전
const HEADER_ALIASES = {
  modelName: ['모델명', '모델', '제품명', '상품명', '모델번호', 'model', '품명', '상품코드'],
  monthlyFee: ['월 구독료', '구독료', '월구독료', '렌탈료', '월렌탈료', '요금', '월요금', '가격', '금액', '월납입금'],
  downPayment: ['계약금', '구독계약금', '초기비용', '가입비', '등록비'],
  period: ['구독 개월 수', '구독 개월수', '구독개월', '개월수', '구독기간', '기간', '약정기간', '약정', '렌탈기간', '개월'],
  category: ['품목', '카테고리', '분류', '종류', '제품군', '품목/상품'],
  careServiceText: ['안심케어1', '정기케어1', '구독패키지', '패키지', '서비스명', '케어명', '서비스', '케어', '관리'],
  careServiceCycle: ['안심케어2', '정기케어2', '주기', '방문주기', '관리주기', '케어주기'],
  careServiceCount: ['횟수', '회수', '방문횟수', '제공횟수'], // 횟수를 명확하게 찾기 위해 안심케어3 제외
  careServiceBenefit: ['안심케어3', '정기케어3', '혜택', '가치', '상당', '금액상당'], // "27만원 상당" 같은 텍스트가 있는 곳
  careServiceDetail: ['안심케어4', '정기케어4', '보증기간', '상세', '서비스내용', '내용']
};

function findColumnIndex(headers: string[], aliases: string[], excludeTokens: string[] = []): number {
  const normalizedHeaders = headers.map(h => h?.toString().replace(/\s+/g, '').toLowerCase() || '');
  const normalizedAliases = aliases.map(a => a.replace(/\s+/g, '').toLowerCase());
  
  // 1. 정확히 일치하는 헤더를 가장 먼저 찾음 (우선순위 최고)
  for (let i = 0; i < normalizedHeaders.length; i++) {
    if (normalizedAliases.includes(normalizedHeaders[i])) {
      return i;
    }
  }

  // 2. 정확히 일치하는 것이 없다면, 포함(부분 일치)되는 헤더를 찾음
  for (let i = 0; i < normalizedHeaders.length; i++) {
    const header = normalizedHeaders[i];
    
    // 오작동 방지: 특정 단어가 포함된 열은 무시 (예: 구독료 찾을 때 '개월수'가 들어간 열은 제외)
    if (excludeTokens.some(ex => header.includes(ex))) {
      continue;
    }
    
    if (normalizedAliases.some(alias => header.includes(alias))) {
      return i;
    }
  }
  return -1;
}

export function parseExcel(file: File): Promise<ProductData[]> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = e.target?.result;
        const workbook = XLSX.read(data, { type: 'binary' });
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        
        const rows = XLSX.utils.sheet_to_json(worksheet, { header: 1 }) as any[][];
        
        // 엑셀에서 헤더(제목) 줄 찾기: 모델명과 관련된 단어가 있는 줄을 유연하게 찾음
        let headerRowIndex = -1;
        let colIndices: Record<string, number> = {};

        for (let i = 0; i < Math.min(rows.length, 20); i++) { // 상위 20줄 이내에서 제목 줄 탐색
          const row = rows[i] || [];
          const headers = row.map(h => h ? h.toString() : '');
          
          const modelIdx = findColumnIndex(headers, HEADER_ALIASES.modelName);
          const feeIdx = findColumnIndex(headers, HEADER_ALIASES.monthlyFee, ['개월']); // '개월'이라는 글자가 들어간 열은 구독료로 인식하지 않음

          // 최소한 모델명과 가격 정보가 있는 줄을 헤더로 간주
          if (modelIdx !== -1 && feeIdx !== -1) {
            headerRowIndex = i;
            colIndices = {
              modelName: modelIdx,
              monthlyFee: feeIdx,
              downPayment: findColumnIndex(headers, HEADER_ALIASES.downPayment),
              period: findColumnIndex(headers, HEADER_ALIASES.period),
              category: findColumnIndex(headers, HEADER_ALIASES.category),
              careServiceText: findColumnIndex(headers, HEADER_ALIASES.careServiceText),
              careServiceCycle: findColumnIndex(headers, HEADER_ALIASES.careServiceCycle),
              careServiceCount: findColumnIndex(headers, HEADER_ALIASES.careServiceCount),
              careServiceBenefit: findColumnIndex(headers, HEADER_ALIASES.careServiceBenefit),
              careServiceDetail: findColumnIndex(headers, HEADER_ALIASES.careServiceDetail),
            };
            break;
          }
        }

        if (headerRowIndex === -1) {
          throw new Error('엑셀 파일에서 "제품명(모델명)"과 "가격(구독료)" 항목을 찾을 수 없습니다.');
        }

        const products: ProductData[] = [];

        for (let i = headerRowIndex + 1; i < rows.length; i++) {
          const row = rows[i];
          if (!row || row.length === 0) continue;
          
          const modelName = row[colIndices.modelName]?.toString().trim();
          if (!modelName) continue;

          // 숫자, 소수점 처리 (예: 31413.055 -> 31413)
          const rawFee = row[colIndices.monthlyFee]?.toString() || '0';
          const monthlyFee = Math.floor(parseFloat(rawFee.replace(/,/g, '').replace(/[^0-9.-]/g, ''))) || 0;
          
          if (monthlyFee <= 0) continue; // 구독료가 0원이면 제외

          const rawPeriod = colIndices.period !== -1 ? (row[colIndices.period]?.toString() || '') : '';
          const period = parseInt(rawPeriod.replace(/[^0-9]/g, '')) || 0;

          const rawDown = colIndices.downPayment !== -1 ? (row[colIndices.downPayment]?.toString() || '0') : '0';
          const downPayment = Math.floor(parseFloat(rawDown.replace(/,/g, '').replace(/[^0-9.-]/g, ''))) || 0;
          
          const rawRowText = row.map((cell: any) => cell ? cell.toString() : '').join(' ');

          products.push({
            id: crypto.randomUUID(),
            category: colIndices.category !== -1 ? (row[colIndices.category]?.toString() || '') : '',
            modelName,
            period,
            monthlyFee,
            downPayment,
            careServiceText: colIndices.careServiceText !== -1 ? (row[colIndices.careServiceText]?.toString() || '') : '',
            careServiceCycle: colIndices.careServiceCycle !== -1 ? (row[colIndices.careServiceCycle]?.toString() || '') : '',
            careServiceCount: colIndices.careServiceCount !== -1 ? (row[colIndices.careServiceCount]?.toString() || '') : '',
            careServiceBenefit: colIndices.careServiceBenefit !== -1 ? (row[colIndices.careServiceBenefit]?.toString() || '') : '',
            careServiceDetail: colIndices.careServiceDetail !== -1 ? (row[colIndices.careServiceDetail]?.toString() || '') : '',
            imageUrl: '',
            changeStatus: 'new',
            rawRowText
          });
        }

        resolve(products);
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = (error) => reject(error);
    reader.readAsBinaryString(file);
  });
}
