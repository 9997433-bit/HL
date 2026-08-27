/**
 * 拼音的小工具。
 *
 * 拼字类玩法要把「shàng」拆成 s / h / a / n / g 这样一个个字母摆出来，
 * 带调的元音必须先还原成不带调的本体，否则孩子会看到 à 和 a 两种同一个字母。
 * ü 不还原成 u —— 它在拼音里是另一个字母，「绿 lǜ」拼成 lu 就错了。
 */

/** 带调元音 → 不带调本体。ü 保留自己，只脱调号。 */
const TONE_MAP = {
  ā: 'a', á: 'a', ǎ: 'a', à: 'a',
  ē: 'e', é: 'e', ě: 'e', è: 'e', ê: 'e',
  ī: 'i', í: 'i', ǐ: 'i', ì: 'i',
  ō: 'o', ó: 'o', ǒ: 'o', ò: 'o',
  ū: 'u', ú: 'u', ǔ: 'u', ù: 'u',
  ǖ: 'ü', ǘ: 'ü', ǚ: 'ü', ǜ: 'ü',
  ń: 'n', ň: 'n', ǹ: 'n',
  ḿ: 'm'
}

/** 去掉声调，得到纯字母的拼音（ü 仍是 ü）。 */
export function toneless(pinyin = '') {
  return [...String(pinyin)]
    .map((ch) => TONE_MAP[ch] ?? ch)
    .join('')
    .toLowerCase()
}

/**
 * 拆成一个个字母，供拼字玩法摆字母牌用。
 * 空格、连字符这类分隔符直接丢掉，只留能点的字母。
 */
export function pinyinLetters(pinyin = '') {
  return [...toneless(pinyin)].filter((ch) => /[a-zü]/.test(ch))
}

export default { toneless, pinyinLetters }
