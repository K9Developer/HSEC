// have funcs to get account from cookies, etc.

import type { User } from "../types";

export class UserManager {
    static getLocalUser() {
        // sample data
        return {
            id: "123",
            email: "a@gmail.com",
            logged_in: true,
            session_token: "abc123",
        } as User;
    }
}