import { toast } from "react-toastify";

const TOAST_OPTIONS = {
    position: 'bottom-center',
    draggable: true,
    closeOnClick: true,
    className: 'bg-darkpurple text-foreground mx-2 mb-1 w-[98%] shadow-[1px_-7px_63px_4px_rgba(0,0,0,0.75)]',
    role: 'alert',
    theme: 'dark'
}

const showPopup = (message: string, type: "error" | "success" | "info" | "warning" = "info", options: any = {}) => {
    const toastOptions = { ...TOAST_OPTIONS, ...options, type };
    toast(message, toastOptions);
};

export default showPopup;