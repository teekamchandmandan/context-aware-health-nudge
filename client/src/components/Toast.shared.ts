export interface ToastItem {
  id: number;
  message: string;
}

let nextToastId = 1;

export function createToastId() {
  return nextToastId++;
}
