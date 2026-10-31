/** Lưu chữ thành tệp ở máy người chơi. Chữ đã tải qua client API (lớp mock trả lời được), nên ở
 *  đây chỉ tạo Blob, không trỏ đường dẫn tới API. */
export function saveTextFile(filename: string, text: string): void {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.rel = 'noopener';
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Thu hồi sau khi trình duyệt đã nhận lượt tải.
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}
