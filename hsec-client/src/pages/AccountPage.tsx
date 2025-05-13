import React, { useEffect } from "react";
import type { User } from "../types";
import { UserManager } from "../utils/AccountManager";

const LoggedInPage = () => {
    return <>Logged In</>;
};

const LoggedOutPage = () => {
    return <>Logged Out</>;
};

const AccountPage = () => {
    const [user, setUser] = React.useState<null | User>(null);

    useEffect(() => {
        setUser(UserManager.getLocalUser());
    }, []);

    return user?.logged_in && user?.session_token ? <LoggedInPage /> : <LoggedOutPage />;
};

export default AccountPage;
