import { useRef, type KeyboardEvent, type ReactNode } from 'react';
import { cx } from './ui';

// Nhóm lựa chọn một: `role="radiogroup"` + `role="radio"`, `aria-checked`, focus lưu động và phím
// mũi tên (WAI-ARIA APG, Radio Group). Chọn chỉ đổi trạng thái tại chỗ; gửi máy chủ ở nút riêng.

export interface RadioOption<K extends string> {
  key: K;
  disabled?: boolean;
}

export function RadioGroup<K extends string, O extends RadioOption<K>>({
  options,
  value,
  onChange,
  label,
  labelledBy,
  className,
  optionClassName,
  render,
  allowDeselect = false,
}: {
  options: O[];
  value: K | null;
  onChange: (key: K | null) => void;
  label?: string;
  labelledBy?: string;
  className?: string;
  optionClassName?: string | ((o: O, checked: boolean) => string);
  render: (o: O, checked: boolean) => ReactNode;
  allowDeselect?: boolean;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const enabled = options.map((o, i) => (o.disabled ? -1 : i)).filter((i) => i >= 0);
  const current = options.findIndex((o) => o.key === value);
  // Chưa chọn gì thì phần tử bật đầu tiên nhận Tab (không chọn sẵn).
  const tabStop = current >= 0 ? current : (enabled[0] ?? -1);

  const move = (from: number, delta: number) => {
    if (enabled.length === 0) return;
    const pos = enabled.indexOf(from);
    const next = enabled[(pos + delta + enabled.length) % enabled.length] ?? enabled[0] ?? 0;
    refs.current[next]?.focus();
    const opt = options[next];
    if (opt) onChange(opt.key);
  };

  const onKey = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
      e.preventDefault();
      move(i, 1);
    } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
      e.preventDefault();
      move(i, -1);
    }
  };

  return (
    <div role="radiogroup" aria-label={label} aria-labelledby={labelledBy} className={className}>
      {options.map((o, i) => {
        const checked = o.key === value;
        const cls = typeof optionClassName === 'function' ? optionClassName(o, checked) : optionClassName;
        return (
          <button
            key={o.key}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={checked}
            aria-disabled={o.disabled || undefined}
            disabled={o.disabled}
            tabIndex={i === tabStop ? 0 : -1}
            onClick={() => onChange(checked && allowDeselect ? null : o.key)}
            onKeyDown={(e) => onKey(e, i)}
            className={cx('text-left', cls)}
          >
            {render(o, checked)}
          </button>
        );
      })}
    </div>
  );
}
