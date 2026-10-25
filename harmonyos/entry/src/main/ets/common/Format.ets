function twoDigits(value: number): string {
  return value < 10 ? '0' + value.toString() : value.toString();
}

export function formatClock(date: Date): string {
  return twoDigits(date.getHours()) + ':' + twoDigits(date.getMinutes()) + ':' + twoDigits(date.getSeconds());
}

export function formatTimestamp(value: string): string {
  if (value.length === 0) {
    return '时间未知';
  }
  return value.replace('T', ' ').replace('Z', ' UTC');
}

export function shortId(value: string): string {
  if (value.length <= 12) {
    return value;
  }
  return value.substring(0, 8) + '…';
}

export function readableError(error: Error): string {
  const message: string = error.message;
  return message.length > 0 ? message : '未知错误';
}
