/**
 * 从自然语言搜索词中推理提取出行信息
 * 例: "杭州1日游" → { destination: "杭州", days: 1 }
 *     "三亚5天亲子游预算1万" → { destination: "三亚", days: 5, budget: 10000 }
 *     "2人成都3日美食游预算5000" → { destination: "成都", travelers: 2, days: 3, budget: 5000 }
 */
export interface ParsedTrip {
  origin: string
  destination: string
  days: number | null
  travelers: number | null
  budget: number | null
  startDate: string
  endDate: string
  query: string
}

export function parseTripQuery(input: string): ParsedTrip {
  const result: ParsedTrip = {
    origin: '',
    destination: '',
    days: null,
    travelers: null,
    budget: null,
    startDate: '',
    endDate: '',
    query: input,
  }

  if (!input.trim()) return result

  let text = input.trim()

  // 0. 提取 "A到B" 模式的出发地和目的地（如"深圳到杭州"）
  // 非贪婪 {2,4}? + 前瞻：避免吃掉"亲子""家庭"等修饰词
  const toMatch = text.match(/^([\u4e00-\u9fa5]{2,4})到([\u4e00-\u9fa5]{2,4}?)(?=游|日|天|亲子|家庭|情侣|蜜月|美食|文化|古城|之旅|[0-9，,。,\-—预算人位])/)
  if (toMatch) {
    result.origin = toMatch[1]
    result.destination = toMatch[2]
    text = text.replace(toMatch[0], '')
  }

  // 0b. 提取出发地 ("上海出发" "从北京" etc)
  if (!result.origin) {
    const originMatch = text.match(/(从|出发地?[：:]\s*)([\u4e00-\u9fa5]{2,4})/)
    if (originMatch) {
      result.origin = originMatch[2].replace(/出发$/, '')  // 去掉尾部"出发"
      text = text.replace(originMatch[0], '')
    }
  }

  // 1. 提取预算 (1万/10000/五千/5000/1k)
  const budgetPatterns = [
    /预算\s*(\d+)\s*[万w]/i,
    /(\d+)\s*[万w]预算/i,
    /预算\s*(\d{4,})/,
    /(\d{4,})\s*预算/,
    /预算\s*([一二三四五六七八九])\s*[千万百]/,
  ]
  for (const pat of budgetPatterns) {
    const m = text.match(pat)
    if (m) {
      let val = parseInt(m[1])
      if (isNaN(val)) {
        const cnMap: Record<string, number> = { 一:1,二:2,三:3,四:4,五:5,六:6,七:7,八:8,九:9 }
        val = cnMap[m[1]] || 0
      }
      if (pat.source.includes('[万w]') || m[0].includes('万')) val *= 10000
      else if (m[0].includes('千')) val *= 1000
      result.budget = val
      text = text.replace(m[0], '')
      break
    }
  }

  // 2. 提取人数 (2人/两人/3个人)
  const travelerPatterns = [
    /(\d+)\s*人/,
    /([两二三四五六七八九十])\s*人/,
    /(\d+)\s*位/,
  ]
  for (const pat of travelerPatterns) {
    const m = text.match(pat)
    if (m) {
      let val = parseInt(m[1])
      if (isNaN(val)) {
        const cnNum: Record<string, number> = { 两:2,二:2,三:3,四:4,五:5,六:6,七:7,八:8,九:9,十:10 }
        val = cnNum[m[1]] || 0
      }
      if (val > 0 && val <= 20) {
        result.travelers = val
        text = text.replace(m[0], '')
        break
      }
    }
  }

  // 亲子游 → 默认2人（1大人+1小孩）
  if (!result.travelers && /亲子/.test(text)) {
    result.travelers = 2
    text = text.replace(/亲子/g, '')
  }
  // 情侣/蜜月 → 默认2人
  if (!result.travelers && /(情侣|蜜月|二人|双人)/.test(text)) {
    result.travelers = 2
    text = text.replace(/情侣|蜜月|二人|双人/g, '')
  }

  // 3. 提取天数 (5天/3日/两天/一周)
  const dayPatterns = [
    /(\d+)\s*天/,
    /(\d+)\s*日/,
    /([两二三四五六七八九十])\s*天/,
    /([两二三四五六七八九十])\s*日/,
    /一周/,
    /周末/,
  ]
  for (const pat of dayPatterns) {
    const m = text.match(pat)
    if (m) {
      let val: number
      if (m[0] === '一周') val = 7
      else if (m[0] === '周末') val = 2
      else {
        val = parseInt(m[1])
        if (isNaN(val)) {
          const cnNum: Record<string, number> = { 两:2,二:2,三:3,四:4,五:5,六:6,七:7,八:8,九:9,十:10 }
          val = cnNum[m[1]] || 0
        }
      }
      if (val > 0 && val <= 30) {
        result.days = val
        text = text.replace(m[0], '')
        break
      }
    }
  }

  // 4. 提取目的地 — 如果尚未从"A到B"模式提取到
  if (!result.destination) {
    const prefixes = ['带家人', '带父母', '带孩子', '带娃', '情侣', '蜜月', '一个人', '独自', '闺蜜', '兄弟']
    let cleanText = text
    for (const prefix of prefixes) {
      if (cleanText.startsWith(prefix)) {
        cleanText = cleanText.slice(prefix.length)
        break
      }
    }
    cleanText = cleanText.replace(/^\\d+\\s*人/, '')
    cleanText = cleanText.trim()
    cleanText = cleanText.replace(/(游|美食|文化|古城|之旅)$/, '')
    const cityMatch = cleanText.match(/^[\u4e00-\u9fa5]{2,3}/)
    if (cityMatch) {
      result.destination = cityMatch[0]
    }
  }

  // 5. 推断日期 (如果用户没指定，默认从明天开始)
  const today = new Date()
  if (result.days) {
    const start = new Date(today)
    start.setDate(start.getDate() + 1) // 明天
    const end = new Date(start)
    end.setDate(end.getDate() + result.days - 1)
    result.startDate = start.toISOString().split('T')[0]
    result.endDate = end.toISOString().split('T')[0]
  }

  return result
}
