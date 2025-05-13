export interface Camera {
    id: string;
    name: string;
    last_frame: string;
    ip: string;
    mac: string;
}

export interface User {
    id: string;
    email: string;
    logged_in: boolean;
    session_token: string | null;
}

export interface LoginResponse {
    success: boolean;
    message: string;
    user: User | null;
}
