import React, { useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { Camera } from "../types";
import { PuffLoader } from "react-spinners";
import { IoMdArrowRoundBack } from "react-icons/io";
import { IconContext } from "react-icons";
import { DataManager } from "../utils/DataManager";
import Button from "../components/Button";
import Input from "../components/Input";

const PasswordResetPage = ({ email, onSuccess, timeLeft }: { email: string, onSuccess: any, timeLeft: number }) => {
    const [code, setCode] = React.useState("");
    const [password, setPassword] = React.useState("");
    const [loading, setLoading] = React.useState(false);

    const validPassword = (password: string) => password.length >= 8;

    return (
        <div className="flex flex-col bg-darkpurple h-full">
            <div className="absolute w-full top-0">
                <div className="p-3 bg-mediumpurple" onClick={() => window.history.back()}>
                    <IconContext.Provider value={{ className: "text-foreground" }}>
                        <IoMdArrowRoundBack size={30} />
                    </IconContext.Provider>
                </div>
            </div>

            <div className="bg-darkpurple h-full w-full flex flex-col items-center justify-center p-8 gap-0">
                <div className="w-full font-bold text-xl text-foreground text-center">Forgot Password</div>
                 {timeLeft > 0 && (
                        <div className="text-foreground text-sm mb-4 mt-1">
                            Code will expire in {Math.floor(timeLeft / 60)}:{("0" + (timeLeft % 60)).slice(-2)}
                        </div>
                    )}
                <Input
                    placeholder="CODE"
                    className="w-full"
                    startingValue=""
                    onChange={(curr: string) => {
                        setCode(curr);
                        return true;
                    }}
                    pattern={/^[0-9]{6}$/}
                />

                <Input
                    placeholder="NEW PASSWORD"
                    className="w-full"
                    startingValue=""
                    onChange={(curr: string) => {
                        setPassword(curr);
                        return true;
                    }}
                    pattern={/^.{8,}$/}
                    type="password"
                />

                <Button
                    className="w-full mt-10"
                    text={"Reset Password"}
                    isLoading={loading}
                    disabled={!validPassword(password) || code.length !== 6}
                    onClick={async () => {
                        setLoading(true);
                        DataManager.resetPassword(email, code, password).then((res: any) => {
                            setLoading(false);
                            if (res.success) {
                                alert("Password reset successfully. You can now log in with your new password.");
                                onSuccess();
                            } else {
                                alert("Failed to reset password: " + res.reason);
                            }
                        }
                        )
                    }}
                />
            </div>
        </div>
    );
}

const ForgotPasswordPage = () => {
    const [email, setEmail] = React.useState("");
    const [awaitingCode, setAwaitingCode] = React.useState(false);
    const [loading, setLoading] = React.useState(false);
    const navigate = useNavigate();
    const [timeRemaining, setTimeRemaining] = React.useState(0);

    const validEmail = (email: string) => {
        return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email);
    }

    useEffect(() => {
        if (timeRemaining > 0) {
            const timer = setInterval(() => {
                setTimeRemaining(prev => {
                    if (prev <= 0) {
                        clearInterval(timer);
                        navigate("/account");
                        alert("Code expired. Please request a new code.");
                        return 0;
                    }
                    return prev - 1;
                });
            }, 1000);
            return () => clearInterval(timer);
        }
    }, [timeRemaining]);

    return (
        awaitingCode ?
            <PasswordResetPage email={email} onSuccess={() => {
                setAwaitingCode(false);
                navigate("/account");
            }} timeLeft={timeRemaining}/>
            :
            <div className="flex flex-col bg-darkpurple h-full">
                <div className="absolute w-full top-0">
                    <div className="p-3 bg-mediumpurple" onClick={() => window.history.back()}>
                        <IconContext.Provider value={{ className: "text-foreground" }}>
                            <IoMdArrowRoundBack size={30} />
                        </IconContext.Provider>
                    </div>
                </div>

                <div className="bg-darkpurple h-full w-full flex flex-col items-center justify-center p-8 gap-5">
                    <div className="w-full font-bold text-xl text-foreground text-center">Forgot Password</div>
                   

                    <Input
                        placeholder="EMAIL"
                        className="w-full"
                        startingValue=""
                        onChange={(curr: string) => {
                            setEmail(curr);
                            return true;
                        }}
                        pattern={/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/}
                    />
                    <Button
                        className="w-full"
                        text={"Send Code"}
                        isLoading={loading}
                        disabled={!validEmail(email)}
                        onClick={async () => {
                            setLoading(true);
                            DataManager.requestPasswordReset(email).then((res: any) => {
                                setLoading(false);
                                if (res.success) {
                                    alert("Code sent to your email. Please check your inbox.");
                                    setTimeRemaining(res.timeLeft);
                                    setAwaitingCode(true);
                                    setLoading(false);
                                } else {
                                    alert("Failed to send code: " + res.reason);
                                    setLoading(false);
                                }
                            })
                        }}
                    />
                </div>
            </div>
    );
};

export default ForgotPasswordPage;
