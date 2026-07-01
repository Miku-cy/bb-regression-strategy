import { useState } from 'react';

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  description?: string;
  onChange: (value: number) => void;
}

export default function Slider({ label, value, min, max, step, unit, description, onChange }: SliderProps) {
  const [editing, setEditing] = useState(false);
  const [inputValue, setInputValue] = useState(String(value));

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  const handleInputBlur = () => {
    const num = parseFloat(inputValue);
    if (!isNaN(num) && num >= min && num <= max) {
      onChange(num);
    } else {
      setInputValue(String(value));
    }
    setEditing(false);
  };

  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleInputBlur();
    } else if (e.key === 'Escape') {
      setInputValue(String(value));
      setEditing(false);
    }
  };

  const percent = ((value - min) / (max - min)) * 100;

  return (
    <div style={{ marginBottom: '14px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
        <label style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-secondary)' }}>
          {label}
        </label>
        {editing ? (
          <input
            type="number"
            value={inputValue}
            onChange={handleInputChange}
            onBlur={handleInputBlur}
            onKeyDown={handleInputKeyDown}
            autoFocus
            step={step}
            min={min}
            max={max}
            style={{
              width: '70px',
              padding: '2px 6px',
              border: '1px solid var(--border-focus)',
              borderRadius: '4px',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              textAlign: 'right',
              outline: 'none',
            }}
          />
        ) : (
          <span
            onClick={() => { setInputValue(String(value)); setEditing(true); }}
            style={{
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              fontWeight: 600,
              color: 'var(--primary)',
              cursor: 'text',
              padding: '2px 6px',
              borderRadius: '4px',
              background: 'var(--primary-bg)',
              minWidth: '50px',
              textAlign: 'right',
              display: 'inline-block',
            }}
          >
            {Number.isInteger(step) ? value : value.toFixed(2)}
            {unit && <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginLeft: '2px' }}>{unit}</span>}
          </span>
        )}
      </div>
      <div style={{ position: 'relative' }}>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          style={{
            background: `linear-gradient(to right, var(--primary) 0%, var(--primary) ${percent}%, var(--border) ${percent}%, var(--border) 100%)`
          }}
        />
      </div>
      {description && (
        <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '3px' }}>
          {description}
        </div>
      )}
    </div>
  );
}
