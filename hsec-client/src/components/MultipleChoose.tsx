import React, { useState } from "react";

interface CheckboxProps {
  checked: boolean;
  label: string;
  onToggle: () => void;
  disabled?: boolean;
}

function Checkbox({ checked, label, onToggle, disabled = false }: CheckboxProps) {
  return (
    <label className={"flex items-center gap-3 select-none group" + (disabled ? " cursor-not-allowed opacity-50" : "cursor-pointer")}>
      <span
        className={`
          relative w-6 h-6 rounded-md border-2 flex items-center justify-center transition-colors
          border-lighterpurple
          ${checked ? "bg-lightblue border-lightblue" : "bg-mediumpurple"}
          group-hover:border-lightblue
        `}
        onClick={(e) => {
          e.preventDefault();
          if (!disabled) {
            onToggle();
          }
        }}
        tabIndex={0}
        aria-checked={checked}
        role="checkbox"
      >
        {checked && (
          <svg className="w-4 h-4 text-foreground" viewBox="0 0 20 20" fill="none">
            <path d="M6 10.5l3 3 5-6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        )}
      </span>
      <span className={`text-foreground font-medium`}>{label}</span>
    </label>
  );
}

interface MultipleChooseProps {
  items: string[];
  startValues: string[];
  onChange: (values: string[]) => void;
  disabled?: boolean;
}

function MultipleChoose({ items, startValues, onChange, disabled = false }: MultipleChooseProps) {
  const [selected, setSelected] = useState<string[]>(startValues);

  function toggleItem(item: string) {
    let newSelected;
    if (selected.includes(item)) {
      newSelected = selected.filter(v => v !== item);
    } else {
      newSelected = [...selected, item];
    }
    setSelected(newSelected);
    onChange(newSelected);
  }

  return (
    <div className="space-y-3">
      {items.map(item => (
        <Checkbox
          key={item}
          label={item}
          checked={selected.includes(item)}
          disabled={disabled}
          onToggle={() => toggleItem(item)}
        />
      ))}
    </div>
  );
}

export default MultipleChoose;