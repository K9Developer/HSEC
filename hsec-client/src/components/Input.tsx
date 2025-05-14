import React from "react";

interface Props {
    placeholder?: string;
    startingValue?: string;
    pattern?: RegExp;
    onChange?: (value: string, matchesPattern: boolean) => boolean | void;
    className?: string;
    type?: string;
    disabled?: boolean;
}

const Input = ({ placeholder, startingValue, pattern, onChange, className, type, disabled }: Props) => {
    const [value, setValue] = React.useState<string>(startingValue || "");
    const [focused, setFocused] = React.useState<boolean>(false);
    const [valid, setValid] = React.useState<boolean>(true);

    return (
        <div className={"relative mt-5 bg-inherit " + className}>
            <input
                type={type || "text"}
                className={
                    "p-2 px-3 rounded-lg text-foreground outline-none focus:outline-none w-full border-[1px] bg-transparent " +
                    (valid ? "border-lightpurple" : "border-red-500")
                }
                value={value}
                disabled={disabled}
                onFocus={() => setFocused(true)}
                onBlur={() => {
                    setFocused(false);
                }}
                onChange={(e) => {
                    const newValue = e.target.value;
                    const isMatch = pattern ? pattern.test(newValue) : true;
                    setValid(isMatch);
                    if (onChange) {
                        const allow = onChange(newValue, isMatch);
                        if (allow === undefined && !isMatch) {
                            setValue(value);
                            return;
                        }
                        if (allow !== false) {
                            setValue(newValue);
                        } else {
                            setValue(value);
                        }
                    } else {
                        setValue(newValue);
                    }
                }}
            />
            {placeholder && (
                <label
                    className={`absolute left-[10px] px-3 transition-all pointer-events-none bg-inherit ${
                        focused || value ? "-top-1/4 text-xs" : "top-1/2 -translate-y-1/2"
                    } ${valid ? "text-lightpurple" : "text-red-500"}`}
                >
                    {placeholder}
                </label>
            )}
        </div>
    );
};

export default Input;
