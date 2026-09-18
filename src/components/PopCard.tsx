import React, { useRef, useState, useEffect } from 'react';
import { ProductData, CardBenefit, CARD_BENEFITS } from '../types';

interface PopCardProps {
  product: ProductData;
  cardBenefit: CardBenefit;
}

export default function PopCard({ product, cardBenefit }: PopCardProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const availableWidth = entry.contentRect.width;
        const targetWidth = 561.26; // 148.5mm in pixels at 96 DPI
        setScale(availableWidth < targetWidth ? availableWidth / targetWidth : 1);
      }
    });
    
    if (containerRef.current) {
      observer.observe(containerRef.current);
    }
    
    return () => observer.disconnect();
  }, []);

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('ko-KR').format(num);
  };

  // 60개월 구독은 무조건 롯데카드로 강제 세팅
  const is60Months = product.period === 60;
  const activeCardBenefit = is60Months 
    ? (CARD_BENEFITS.find(c => c.name.includes('롯데')) || cardBenefit)
    : cardBenefit;

  const perceivedPrice = Math.max(0, product.monthlyFee - activeCardBenefit.discount);
  
  // 계산된 계약금 및 최종 혜택가 (유저 요청)
  const calculatedDownPayment = product.monthlyFee * product.period;
  const totalBenefitPrice = perceivedPrice * product.period;

  // 3년/5년 AS 자동 판단 로직 초강화 (엑셀의 모든 셀 내용을 공백 없이 검사)
  const allText = (product.rawRowText || Object.values(product).join(' ')).replace(/\s+/g, '');
  const is3Years = allText.includes('3년') || allText.includes('안심케어3') || allText.includes('정기케어3');
  const warrantyYears = is3Years ? '3' : '5';

  return (
    <div ref={containerRef} className="w-full flex justify-center print:w-full print:h-full">
      {/* Screen scale wrapper: reserves space on screen, transparent on print */}
      <div 
        className="relative print:!w-full print:!h-full"
        style={{ width: `${561.26 * scale}px`, height: `${793.7 * scale}px` }}
      >
        <div 
          className="w-[148.5mm] h-[210mm] bg-white border-8 border-slate-800 px-6 pt-6 pb-10 flex flex-col shadow-lg box-border shrink-0 origin-top-left absolute top-0 left-0 print:!relative print:!transform-none print:w-full print:h-full print:border-[8px] print:shadow-none print:m-0"
          style={{ transform: `scale(${scale})` }}
        >
          {/* Top Section */}
          <div className="text-center mb-2">
        <div className="flex justify-center gap-1 mb-1">
          {[...Array(5)].map((_, i) => (
            <svg key={i} className="w-5 h-5 text-yellow-400 fill-current" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
          ))}
        </div>
        
        {/* Status Badge (Only visible on screen, hidden on print) */}
        {product.changeStatus === 'new' && (
          <div className="absolute top-4 right-4 bg-green-500 text-white px-2 py-1 rounded text-xs font-bold no-print shadow-sm">
            NEW 새로추가
          </div>
        )}
        {product.changeStatus === 'changed' && (
          <div className="absolute top-4 right-4 bg-slate-1000 text-white px-2 py-1 rounded text-xs font-bold no-print shadow-sm">
            UPDATE 가격변동
          </div>
        )}

        <h1 className="text-3xl font-black text-slate-800 tracking-tight leading-tight">
          구독하면 <span className="text-blue-700 italic text-4xl">더!</span> 합리적인 선택
        </h1>
        <div className="mt-2 bg-slate-800 text-white inline-flex items-center px-4 py-1.5 rounded-full text-sm font-bold shadow-md">
          <span className="text-yellow-400 mr-2">초기 비용 부담 ZERO!</span>
          <span className="border-l border-slate-500 pl-2">초기 부담 없이 바로 시작하세요!</span>
        </div>
      </div>

      {/* Main Price Box */}
      <div className="border-2 border-slate-200 rounded-xl mt-4 p-3 relative flex-1 flex flex-col items-center justify-center bg-slate-50">
        <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-yellow-500 text-slate-900 font-bold px-6 py-1.5 rounded-full text-base flex items-center shadow-md border-2 border-white whitespace-nowrap">
          <span className="mr-2 text-lg">💳</span> 제휴카드 적용 시
        </div>
        
        <h2 className="text-xl font-bold text-slate-700 mb-0 mt-3">월 체감가 ✨</h2>
        <div className="flex items-end text-red-600 font-black tracking-tighter">
          <span className="text-[4.8rem] leading-none">{formatNumber(perceivedPrice)}</span>
          <span className="text-2xl mb-2 ml-2">원</span>
        </div>
        
        {/* 구독 계약금 및 최종 혜택가 */}
        <div className="mt-1 bg-slate-200/70 text-slate-700 text-xs font-bold px-4 py-1.5 rounded-lg flex items-center justify-center gap-3 w-full">
          <span>총 구독 원금 <span className="text-slate-900 ml-1">{formatNumber(calculatedDownPayment)}원</span></span>
          <span className="text-slate-400">|</span>
          <span>총 구독 체감가 <span className="text-red-600 ml-1">{formatNumber(totalBenefitPrice)}원</span></span>
        </div>
        <p className="text-[10px] text-slate-500 mt-1 font-medium">※ 월 30만원 사용 기준</p>
      </div>

      {/* Info Row */}
      <div className="grid grid-cols-3 gap-3 mt-4">
        <div className="border border-slate-200 rounded-lg p-3 text-center bg-white shadow-sm flex flex-col justify-center">
          <div className="text-xs font-bold text-slate-500 mb-1 flex items-center justify-center gap-1">
            <span>🗓️</span> 월 구독료
          </div>
          <div className="font-extrabold text-slate-800 text-lg">{formatNumber(product.monthlyFee)}원</div>
        </div>
        <div className="border border-slate-200 rounded-lg p-3 text-center bg-white shadow-sm flex flex-col justify-center">
          <div className="text-xs font-bold text-slate-500 mb-1 flex items-center justify-center gap-1">
            <span>⏳</span> 구독기간
          </div>
          <div className="font-extrabold text-slate-800 text-lg">{product.period}개월</div>
        </div>
        <div className="border border-slate-200 rounded-lg p-3 text-center bg-white shadow-sm flex flex-col justify-center">
          <div className="text-[10px] font-bold text-slate-500 mb-0.5 flex items-center justify-center gap-1">
            <span>🏷️</span> 제품 모델명
            {product.category && <span className="text-blue-600 ml-1 font-black">[{product.category}]</span>}
          </div>
          <div className="font-bold text-slate-800 text-[11px] break-all leading-tight">
            {product.modelName}
          </div>
        </div>
      </div>

      {/* Card Benefit Banner */}
      <div className="mt-4 bg-slate-800 rounded-xl p-4 flex items-center justify-between shadow-md">
        <div className="flex flex-col w-24">
          <span className="bg-blue-600 text-white text-[10px] px-2 py-0.5 rounded uppercase font-bold self-start mb-1 text-center w-full">{activeCardBenefit.name.replace('카드', '제휴카드')}</span>
          <span className="text-slate-300 text-[10px] font-medium text-center">월 30만원 사용 시</span>
        </div>
        <div className="text-center flex-1">
          <div className="text-yellow-400 font-black text-[1.7rem] leading-none tracking-tight">
            {formatNumber(activeCardBenefit.discount)}원 {activeCardBenefit.benefitType}
          </div>
          <div className="text-slate-300 text-[10px] mt-1.5 font-bold">매월 {activeCardBenefit.benefitType}으로 지급!</div>
        </div>
      </div>

      {/* 3 Bottom Boxes */}
      <div className="grid grid-cols-3 gap-2 mt-4 h-36">
        {/* Box 1 */}
        <div className="border border-slate-800 rounded-lg overflow-hidden flex flex-col text-[10px]">
          <div className="bg-slate-800 text-white text-center py-1.5 font-bold">구독 케어 서비스</div>
          <div className="p-2 flex-1 flex flex-col justify-start gap-1">
            {/* 명칭, 주기, 횟수 등을 가독성 있게 구조화 */}
            {(product.careServiceText || product.careServiceCycle || product.careServiceCount || product.careServiceBenefit) && (
              <div className="border-b border-slate-200 pb-1.5">
                {product.careServiceText && (
                  <div className="font-bold text-slate-800 break-words leading-tight mb-1">
                    {product.careServiceText}
                  </div>
                )}
                {(product.careServiceCycle || product.careServiceCount || product.careServiceBenefit) && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {product.careServiceCycle && (
                      <span className="bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded text-[9px] font-bold">
                        {/^\d+$/.test(product.careServiceCycle.trim()) ? `${product.careServiceCycle}개월 주기` : product.careServiceCycle}
                      </span>
                    )}
                    {product.careServiceCount && (
                      <span className="bg-slate-100/70 text-blue-700 px-1.5 py-0.5 rounded text-[9px] font-bold">
                        {/^\d+$/.test(product.careServiceCount.trim()) ? `총 ${product.careServiceCount}회` : product.careServiceCount}
                      </span>
                    )}
                    {product.careServiceBenefit && (
                      <span className="bg-green-50 text-green-700 px-1.5 py-0.5 rounded text-[9px] font-bold">
                        {product.careServiceBenefit}
                      </span>
                    )}
                  </div>
                )}
              </div>
            )}
            
            {/* 상세 내용 (데미지 케어 1년, 소모품 배송 등) */}
            {(product.careServiceDetail || (!product.careServiceText && !product.careServiceCycle && !product.careServiceCount && !product.careServiceBenefit && !product.careServiceDetail)) && (
              <div className="flex flex-col mt-0.5">
                <span className="text-slate-500 mb-0.5 text-[9px]">서비스 내용</span>
                <span className="font-bold text-blue-700 break-words leading-tight text-[10px]">
                  {product.careServiceDetail || '해당없음'}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Box 2 */}
        <div className="border border-slate-800 rounded-lg overflow-hidden flex flex-col text-[10px]">
          <div className="bg-slate-800 text-white text-center py-1.5 font-bold">
            {warrantyYears}년 무상 A/S
          </div>
          <div className="p-2 flex-1 flex flex-col items-center justify-center text-center">
            
            {/* 깔끔하고 큼직한 원형 뱃지 */}
            <div className="w-14 h-14 bg-blue-800 text-white rounded-full flex flex-col items-center justify-center border-2 border-dashed border-blue-400 mb-1.5 shadow-sm">
              <span className="text-2xl font-black leading-none">{warrantyYears}</span>
              <span className="text-[9px] font-bold mt-0.5">YEARS</span>
            </div>
            <div className="font-bold text-slate-700 leading-tight text-[11px]">
              <span className="text-blue-800 font-extrabold">{warrantyYears}년간 무상 A/S</span>로<br/>안심하고 사용하세요!
            </div>
          </div>
        </div>

        {/* Box 3 */}
        <div className="border border-slate-800 rounded-lg overflow-hidden flex flex-col text-[10px]">
          <div className="bg-slate-800 text-white text-center py-1.5 font-bold">카드 사용 꿀팁!</div>
          <div className="p-3 flex-1 flex flex-col justify-center gap-1.5">
            {['개인 보험 자동이체', '휴대폰 요금 자동이체', '학원비 자동이체', '생활비 결제'].map((tip, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <svg className="w-3 h-3 text-blue-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                <span className="font-bold text-slate-700">{tip}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer Table */}
      <div className="mt-4 border border-slate-800 rounded-lg overflow-hidden grid grid-cols-2 text-sm font-bold">
        <div className="flex border-r border-slate-800">
          <div className="bg-slate-100 p-2 w-24 text-center border-r border-slate-800 text-slate-600">총 구독원금</div>
          <div className="p-2 flex-1 text-right">{formatNumber(calculatedDownPayment)} 원</div>
        </div>
        <div className="flex">
          <div className="bg-slate-100 p-2 w-24 text-center border-r border-slate-800 text-slate-600">총 구독체감가</div>
          <div className="p-2 flex-1 text-right text-red-600 font-black">{formatNumber(totalBenefitPrice)} 원</div>
        </div>
      </div>

      <p className="text-[8px] text-slate-400 text-center mt-2 font-medium">
        ※ 본 상품은 구독 서비스 상품으로, 중도 해지 시 위약금이 발생할 수 있습니다.
      </p>
        </div>
      </div>
    </div>
  );
}
