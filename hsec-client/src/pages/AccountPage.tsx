import React, { useEffect } from "react";
import type { User } from "../types";
import { UserManager } from "../utils/AccountManager";
import { IconContext } from "react-icons";
import { MdAccountCircle } from "react-icons/md";
import { IoMdArrowRoundBack } from "react-icons/io";
import Input from "../components/Input";
import { Link } from "react-router-dom";
import { DataManager } from "../utils/DataManager";
import Button from "../components/Button";

interface LoggedInProps {
    user: User;
    onLogOut: () => void;
}

const LoggedInPage = ({ user, onLogOut }: LoggedInProps) => {
    return (
        <div className="flex flex-col gap-4 items-center w-full">
            <IconContext.Provider value={{ className: "text-foreground" }}>
                <MdAccountCircle size={50} />
            </IconContext.Provider>
            <p className="text-gray-400 tracking-wider">{user.email}</p>
            <button className="bg-lightblue rounded-md px-4 py-2 font-semibold" onClick={() => onLogOut()}>
                Log Out
            </button>
        </div>
    );
};

interface LoggedOutProps {
    onLogin: (email: string, password: string) => Promise<void>;
    onCreate: (email: string, password: string) => Promise<void>;
}

const LoggedOutPage = ({ onLogin, onCreate }: LoggedOutProps) => {
    const [currentMode, setCurrentMode] = React.useState("login");
    const [email, setEmail] = React.useState("");
    const [password, setPassword] = React.useState("");
    const [loading, setLoading] = React.useState(false);

    const areInputsValid = (email: string, password: string) => {
        console.log(email, password, currentMode, /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email));
        if (email.length === 0 || password.length === 0) return false;
        return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email) && password.length >= 8;
    };

    return (
        <div className="bg-darkpurple h-full w-full flex flex-col items-center justify-center p-8 gap-5">
            <div className="w-full font-bold text-xl text-foreground text-center">LOGIN</div>
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
            <Input
                placeholder="PASSWORD"
                className="w-full"
                startingValue=""
                pattern={/^.{8,}$/}
                onChange={(curr: string) => {
                    setPassword(curr);
                    return true;
                }}
                type="password"
            />
            <div className="w-full flex flex-row justify-between text-foreground-trans mb-4 text-sm">
                <Link to="forgot-pass">Forgot Password</Link>
                <button onClick={() => setCurrentMode(currentMode === "login" ? "create" : "login")}>
                    {currentMode === "login" ? "Create an Account" : "Already have an account?"}
                </button>
            </div>
            <Button
                className="w-full"
                text={currentMode === "login" ? "Login" : "Create Account"}
                isLoading={loading}
                disabled={!areInputsValid(email, password)}
                onClick={async () => {
                    setLoading(true);
                    if (currentMode === "login") await onLogin(email, password);
                    else await onCreate(email, password);
                    setLoading(false);
                }}
            />
        </div>
    );
};

const AccountPage = () => {
    const [user, setUser] = React.useState<null | User>(null);

    const handleLogOut = () => {
        UserManager.logoutUser();
        setUser(null);
    };

    const handleLogin = async (email: string, password: string) => {
        const { token, id } = await DataManager.requestSessionToken(email, password);
        const user = {
            id: id,
            email: email,
            logged_in: true,
            session_token: token,
        } as User;
        UserManager.setLocalUser(user);
        setUser(user);
    };

    const handleCreateAccount = async (email: string, password: string) => {
        const { token, id, success, reason } = await DataManager.createAccount(email, password);
        if (!success) {
            alert(reason);
            return;
        }
        const user = {
            id: id,
            email: email,
            logged_in: true,
            session_token: token,
        } as User;
        UserManager.setLocalUser(user);
        setUser(user);
    };

    useEffect(() => {
        setUser(UserManager.getLocalUser());
    }, []);
    return (
        <div className="flex justify-center items-center h-full bg-darkpurple relative">
            <div className="absolute w-full top-0">
                <div className="p-3 bg-mediumpurple" onClick={() => window.history.back()}>
                    <IconContext.Provider value={{ className: "text-foreground" }}>
                        <IoMdArrowRoundBack size={30} />
                    </IconContext.Provider>
                </div>
            </div>
            {user?.logged_in && user?.session_token ? (
                <LoggedInPage user={user} onLogOut={handleLogOut} />
            ) : (
                <LoggedOutPage onLogin={handleLogin} onCreate={handleCreateAccount} />
            )}
        </div>
    );
};

export default AccountPage;
