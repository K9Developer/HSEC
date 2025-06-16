/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
    darkMode: "class", // enables `dark:` variants using class strategy
    theme: {
        extend: {
            colors: {
                // background: {
                //     light: "#2d2f33", // card/bg2
                //     DEFAULT: "#1c1d21", // main bg
                //     dark: "#131417", // deepest bg
                // },
                // foreground: {
                //     light: "#d0d4da", // soft-light text
                //     DEFAULT: "#f1f2f4", // main text
                //     dark: "#ffffff", // for elevated contrast spots
                // },
                // primary: {
                //     light: "#7f9cf5", // soft indigo-300
                //     DEFAULT: "#6366f1", // indigo-500
                //     dark: "#4f46e5", // indigo-600
                // },
                // secondary: {
                //     light: "#a78bfa", // purple-300 (muted)
                //     DEFAULT: "#8b5cf6", // purple-500
                //     dark: "#6d28d9", // purple-700
                // },
                // accent: {
                //     light: "#fbbf24", // amber-400
                //     DEFAULT: "#f59e0b", // amber-500
                //     dark: "#b45309", // amber-700
                // },
                // success: {
                //     light: "#6ee7b7", // green-300
                //     DEFAULT: "#22c55e", // green-500
                //     dark: "#15803d", // green-700
                // },
                // danger: {
                //     light: "#fca5a5", // red-300
                //     DEFAULT: "#ef4444", // red-500
                //     dark: "#b91c1c", // red-700
                // },
                foreground: "#D1CCE0",
                "foreground-trans": "#D1CCE0AA",
                lighterpurple: "#867CA1",
                lightpurple: "#6F678D",
                mediumpurple: "#342D4E",
                purple: "#20193A",
                darkpurple: "#17112B",
                lightblue: "#00B8FF",
                darkblue: "#05729c",
            },
        },
    },
};
