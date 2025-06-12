export interface Camera {
    name: string;
    last_frame: string;
    ip: string;
    mac: string;
}

export interface User {
    email: string;
    logged_in: boolean;
    session_token: string | null;
}

export interface LoginResponse {
    success: boolean;
    message: string;
    user: User | null;
}

// ---------

export interface GenericResponse {
    success: boolean;
    info: string;
}

export interface GetCamerasResponse extends GenericResponse {
    cameras: Camera[];
}