import type { ReactNode } from 'react';
import { cx } from './ui';

// Nhóm chọn nhiều dạng chip (D-160): mỗi chip là một checkbox thật có nhãn (bàn phím, trình đọc màn hình chạy sẵn).
// `value` giữ thứ tự người chơi chọn; đủ `max` thì chip chưa chọn bị tắt.

export interface ChipOption {
  key: string;
  label: string;
  hint?: string;
}

export function ChipMultiSelect<O extends ChipOption>({
  options,
  value,
  onChange,
  max,
  labelledBy,
  className,
  chipClassName,
  render,
}: {
  options: O[];
  value: string[];
  onChange: (keys: string[]) => void;
  max: number;
  labelledBy: string;
  className?: string;
  chipClassName: (checked: boolean, disabled: boolean) => string;
  render?: (o: O) => ReactNode;
}) {
  const full = value.length >= max;
  return (
    <div role="group" aria-labelledby={labelledBy} className={className}>
      {options.map((o) => {
        const checked = value.includes(o.key);
        const disabled = !checked && full;
        return (
          <label key={o.key} title={o.hint} className={cx(chipClassName(checked, disabled), disabled && 'cursor-not-allowed opacity-50')}>
            <input
              type="checkbox"
              className="sr-only"
              checked={checked}
              disabled={disabled}
              onChange={() => onChange(checked ? value.filter((k) => k !== o.key) : [...value, o.key])}
            />
            {render ? render(o) : o.label}
          </label>
        );
      })}
    </div>
  );
}
