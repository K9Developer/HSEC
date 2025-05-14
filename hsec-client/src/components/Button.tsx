/**<button
                className="w-full bg-lightblue font-semibold py-2 rounded-lg click-effect"
                onClick={() => {
                    if (currentMode === "login") handleLogin(email, password);
                    else handleCreateAccount(email, password);
                }}
            >
                {currentMode === "login" ? "Login" : "Create Account"}
            </button> */
import React from "react";
import { PuffLoader } from "react-spinners";

interface Props {
    text: string;
    onClick?: () => void;
    isLoading?: boolean;
    disabled?: boolean;
    className?: string;
}

const Button = ({ text, onClick, isLoading, disabled, className }: Props) => {
    console.log(disabled);
    return (
        <button
            onClick={onClick}
            disabled={isLoading || disabled}
            className={
                "font-semibold py-2 rounded-lg h-10 flex justify-center px-2 " +
                (disabled ? "bg-inherit border-lightpurple border-[1px] text-lightpurple " : "bg-lightblue ") +
                className
            }
        >
            {isLoading ? <PuffLoader size={25} /> : text}
        </button>
    );
};

export default Button;
