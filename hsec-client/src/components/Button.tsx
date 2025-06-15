import { PuffLoader } from "react-spinners";

interface Props {
    text: string;
    onClick?: () => void;
    isLoading?: boolean;
    disabled?: boolean;
    className?: string;
    icon?: React.ElementType; 
}

const Button = ({ text, onClick, isLoading, disabled, className, icon: Icon }: Props) => {
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
            {isLoading ? <PuffLoader size={25} /> : <div className="flex flex-row gap-3 items-center">
                {Icon && <Icon/>}
                {text}
                </div>}
        </button>
    );
};

export default Button;
