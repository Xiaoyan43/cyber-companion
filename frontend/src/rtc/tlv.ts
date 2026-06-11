/** TLV helpers — ported from volcengine/rtc-aigc-demo src/utils/utils.ts (BSD-3-Clause). */

export function string2tlv(str: string, type: string): ArrayBuffer {
  const typeBuffer = new Uint8Array(4);
  for (let i = 0; i < type.length; i++) {
    typeBuffer[i] = type.charCodeAt(i);
  }

  const valueBuffer = new TextEncoder().encode(str);
  const length = valueBuffer.length;
  const tlvBuffer = new Uint8Array(typeBuffer.length + 4 + valueBuffer.length);

  tlvBuffer.set(typeBuffer, 0);
  tlvBuffer[4] = (length >> 24) & 0xff;
  tlvBuffer[5] = (length >> 16) & 0xff;
  tlvBuffer[6] = (length >> 8) & 0xff;
  tlvBuffer[7] = length & 0xff;
  tlvBuffer.set(valueBuffer, 8);
  return tlvBuffer.buffer;
}

export function tlv2String(tlvBuffer: ArrayBufferLike): { type: string; value: string } {
  const typeBuffer = new Uint8Array(tlvBuffer, 0, 4);
  const lengthBuffer = new Uint8Array(tlvBuffer, 4, 4);
  const valueBuffer = new Uint8Array(tlvBuffer, 8);

  let type = "";
  for (let i = 0; i < typeBuffer.length; i++) {
    type += String.fromCharCode(typeBuffer[i]);
  }

  const length =
    (lengthBuffer[0] << 24) | (lengthBuffer[1] << 16) | (lengthBuffer[2] << 8) | lengthBuffer[3];

  const value = new TextDecoder().decode(valueBuffer.subarray(0, length));
  return { type, value };
}
