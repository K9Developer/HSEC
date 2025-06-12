import React, { useEffect, useRef } from "react";
import { IconContext } from "react-icons";
import { IoMdClose } from "react-icons/io";

interface ModalProps {
    visible: boolean;
    onClose: () => void;
    showCloseButton?: boolean;
    className?: string;
    children: React.ReactNode;
}

const Modal = ({ visible, onClose, showCloseButton = true, className, children }: ModalProps) => {
    const modalRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleEscKey = (event: KeyboardEvent) => {
            if (event.key === "Escape" && visible) {
                onClose();
            }
        };

        document.addEventListener("keydown", handleEscKey);
        return () => {
            document.removeEventListener("keydown", handleEscKey);
        };
    }, [visible, onClose]);

    const handleOverlayClick = (e: React.MouseEvent) => {
        if (modalRef.current && e.target === e.currentTarget) {
            onClose();
        }
    };

    if (!visible) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-80" onClick={handleOverlayClick}>
            <div ref={modalRef} className={`bg-mediumpurple rounded-lg shadow-lg relative p-6 max-w-md w-full mx-4 ${className || ""}`}>
                {showCloseButton && <button
                    onClick={onClose}
                    className="absolute top-3 right-3 text-gray-500 hover:text-gray-700 transition-colors"
                    aria-label="Close modal"
                >
                    <IconContext.Provider value={{ className: "text-foreground" }}>
                        <IoMdClose />
                    </IconContext.Provider>
                </button>}
                <div className="mt-2 bg-inherit">{children}</div>
            </div>
        </div>
    );
};

export default Modal;
