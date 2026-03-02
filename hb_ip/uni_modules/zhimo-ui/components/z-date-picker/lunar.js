// lunar.js (mini) - 仅保留 solar2lunar（用于日历显示农历月/日）
// 数据范围：1900-2100
const lunarInfo = [0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0,
		0x055d2, //1900-1909
		0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977, //1910-1919
		0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970, //1920-1929
		0x06566, 0x0d4a0, 0x0ea50, 0x06e95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950, //1930-1939
		0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557, //1940-1949
		0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5b0, 0x14573, 0x052b0, 0x0a9a8, 0x0e950, 0x06aa0, //1950-1959
		0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0, //1960-1969
		0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b6a0, 0x195a6, //1970-1979
		0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570, //1980-1989
		0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x055c0, 0x0ab60, 0x096d5, 0x092e0, //1990-1999
		0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5, //2000-2009
		0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930, //2010-2019
		0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530, //2020-2029
		0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45, //2030-2039
		0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0, //2040-2049
		0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06b20, 0x1a6c4, 0x0aae0, //2050-2059
		0x0a2e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4, //2060-2069
		0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0, //2070-2079
		0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160, //2080-2089
		0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252, //2090-2099
		0x0d520];
const solarMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

function isLeapYear(y){
  return (y % 4 === 0 && y % 100 !== 0) || (y % 400 === 0);
}

function solarDays(y,m){ // m:1-12
  if(m===2) return isLeapYear(y) ? 29 : 28;
  return solarMonth[m-1];
}

function leapMonth(y){ // 0=无闰月
  return lunarInfo[y-1900] & 0xf;
}

function leapDays(y){
  const lm = leapMonth(y);
  if(lm) return (lunarInfo[y-1900] & 0x10000) ? 30 : 29;
  return 0;
}

function monthDays(y,m){ // m:1-12
  return (lunarInfo[y-1900] & (0x10000 >> m)) ? 30 : 29;
}

function lYearDays(y){
  let sum = 348;
  const info = lunarInfo[y-1900];
  for(let i=0x8000; i>0x8; i>>=1) {
    sum += (info & i) ? 1 : 0;
  }
  return sum + leapDays(y);
}

const monthCn = ['正月','二月','三月','四月','五月','六月','七月','八月','九月','十月','冬月','腊月'];
const nStr1 = ['日','一','二','三','四','五','六','七','八','九','十'];
const nStr2 = ['初','十','廿','卅'];

function toChinaDay(d){
  if(d === 10) return '初十';
  if(d === 20) return '二十';
  if(d === 30) return '三十';
  const two = Math.floor(d/10);
  const one = d%10;
  return nStr2[two] + nStr1[one];
}

/**
 * 公历转农历
 * @param y 年 (1900-2100)
 * @param m 月 (1-12)
 * @param d 日 (1-31)
 * @returns {lYear:number,lMonth:number,lDay:number,isLeap:boolean,IMonthCn:string,IDayCn:string}
 */
export function solar2lunar(y,m,d){
  if(y<1900 || y>2100) throw new Error('year out of range');
  if(m<1 || m>12) throw new Error('month out of range');
  if(d<1 || d>31) throw new Error('day out of range');

  // 以 1900-01-31 为基准（农历 1900 正月初一）
  let offset = 0;
  for(let yy=1900; yy<y; yy++) offset += (isLeapYear(yy)?366:365);
  for(let mm=1; mm<m; mm++) offset += solarDays(y,mm);
  offset += (d - 31); // 1900-01-31 -> offset 0

  let lunarYear = 1900;
  let yearDays = lYearDays(lunarYear);
  while(offset >= yearDays && lunarYear < 2100){
    offset -= yearDays;
    lunarYear++;
    yearDays = lYearDays(lunarYear);
  }

  let leap = leapMonth(lunarYear);
  let isLeap = false;
  let lunarMonth = 1;
  let mdays = 0;

  while(true){
    if(leap && lunarMonth === leap + 1 && !isLeap){
      // 进入闰月
      lunarMonth--;
      isLeap = true;
      mdays = leapDays(lunarYear);
    } else {
      mdays = monthDays(lunarYear, lunarMonth);
    }

    if(offset < mdays) break;

    offset -= mdays;

    if(isLeap && lunarMonth === leap){
      // 退出闰月
      isLeap = false;
    }
    lunarMonth++;
  }

  const lunarDay = offset + 1;

  const IMonthCn = (isLeap ? '闰' : '') + monthCn[lunarMonth-1];
  const IDayCn = toChinaDay(lunarDay);

  return {
    lYear: lunarYear,
    lMonth: lunarMonth,
    lDay: lunarDay,
    isLeap,
    IMonthCn,
    IDayCn
  };
}
