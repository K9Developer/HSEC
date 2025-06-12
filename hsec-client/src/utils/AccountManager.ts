// have funcs to get account from cookies, etc.

import type { User } from "../types";

export class UserManager {
    static getLocalUser(): User | null {
        // sample data
        // return {
        //     id: "123",
        //     email: "a@gmail.com",
        //     logged_in: true,
        //     session_token: "abc123",
        // } as User;

        const user = localStorage.getItem("user");
        if (user) {
            try {
                return JSON.parse(user) as User;
            } catch (e) {
                return null;
            }
        } else {
            return null;
        }
    }

    static logoutUser() {
        localStorage.removeItem("user");
        
    }

    static setLocalUser(user: User) { 
        try {
            localStorage.setItem("user", JSON.stringify({
                ...user,
                logged_in: false,
            }));
        } catch (e) {
            console.error("Failed to set user in local storage:", e);
        }
    }
}