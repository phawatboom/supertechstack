const windows1252Bytes = new Map<string, number>([
  ["\u20ac", 0x80],
  ["\u201a", 0x82],
  ["\u0192", 0x83],
  ["\u201e", 0x84],
  ["\u2026", 0x85],
  ["\u2020", 0x86],
  ["\u2021", 0x87],
  ["\u02c6", 0x88],
  ["\u2030", 0x89],
  ["\u0160", 0x8a],
  ["\u2039", 0x8b],
  ["\u0152", 0x8c],
  ["\u017d", 0x8e],
  ["\u2018", 0x91],
  ["\u2019", 0x92],
  ["\u201c", 0x93],
  ["\u201d", 0x94],
  ["\u2022", 0x95],
  ["\u2013", 0x96],
  ["\u2014", 0x97],
  ["\u02dc", 0x98],
  ["\u2122", 0x99],
  ["\u0161", 0x9a],
  ["\u203a", 0x9b],
  ["\u0153", 0x9c],
  ["\u017e", 0x9e],
  ["\u0178", 0x9f],
]);

const mojibakeRunPattern =
  /(?:[\u00c2\u00c3\u00c5\u00c9\u00e2\u00ee\u00ef][\u0080-\u00bf\u00a0-\u00ff\u0152\u0153\u0160\u0161\u0178\u017d\u017e\u02c6\u02dc\u2018-\u201d\u2020-\u2022\u2026\u2030\u2039\u203a\u20ac]{1,4})+/g;

const internalCitationPattern =
  /(?:[\ue000-\uf8ff]cite(?:[\ue000-\uf8ff][^\ue000-\uf8ff\s]+)+[\ue000-\uf8ff]|\u25a1cite(?:\u25a1[^\u25a1\s]+)+\u25a1)/g;

const unsafeControlPattern = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]/g;
const privateUsePattern = /[\ue000-\uf8ff]/g;

function toWindows1252Bytes(value: string) {
  const bytes: number[] = [];

  for (const char of value) {
    const codePoint = char.codePointAt(0);

    if (codePoint === undefined) {
      return null;
    }

    if (codePoint <= 0xff) {
      bytes.push(codePoint);
      continue;
    }

    const byte = windows1252Bytes.get(char);

    if (byte === undefined) {
      return null;
    }

    bytes.push(byte);
  }

  return new Uint8Array(bytes);
}

function repairMojibake(value: string) {
  return value.replace(mojibakeRunPattern, (match) => {
    const bytes = toWindows1252Bytes(match);

    if (!bytes) {
      return match;
    }

    try {
      return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    } catch {
      return match;
    }
  });
}

export function cleanCopiedText(
  value: string,
  options: { trim?: boolean } = {},
) {
  const cleaned = repairMojibake(value)
    .replace(internalCitationPattern, "")
    .replace(privateUsePattern, "")
    .replace(unsafeControlPattern, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n");

  return options.trim === false ? cleaned : cleaned.trim();
}
