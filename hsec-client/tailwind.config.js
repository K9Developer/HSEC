/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
    darkMode: ["class"], // enables `dark:` variants using class strategy
    theme: {
    	extend: {
    		colors: {
    			foreground: "#D1CCE0",
                "foreground-trans": "#D1CCE0AA",
                lighterpurple: "#867CA1",
                lightpurple: "#6F678D",
                mediumpurple: "#342D4E",
                purple: "#20193A",
                darkpurple: "#17112B",
                lightblue: "#00B8FF",
                darkblue: "#05729c",
    			card: {
    				DEFAULT: 'hsl(var(--card))',
    				foreground: 'hsl(var(--card-foreground))'
    			},
    			popover: {
    				DEFAULT: 'hsl(var(--popover))',
    				foreground: 'hsl(var(--popover-foreground))'
    			},
    			primary: {
    				DEFAULT: 'hsl(var(--primary))',
    				foreground: 'hsl(var(--primary-foreground))'
    			},
    			secondary: {
    				DEFAULT: 'hsl(var(--secondary))',
    				foreground: 'hsl(var(--secondary-foreground))'
    			},
    			muted: {
    				DEFAULT: 'hsl(var(--muted))',
    				foreground: 'hsl(var(--muted-foreground))'
    			},
    			accent: {
    				DEFAULT: 'hsl(var(--accent))',
    				foreground: 'hsl(var(--accent-foreground))'
    			},
    			destructive: {
    				DEFAULT: 'hsl(var(--destructive))',
    				foreground: 'hsl(var(--destructive-foreground))'
    			},
    			border: 'hsl(var(--border))',
    			input: 'hsl(var(--input))',
    			ring: 'hsl(var(--ring))',
    			chart: {
    				'1': 'hsl(var(--chart-1))',
    				'2': 'hsl(var(--chart-2))',
    				'3': 'hsl(var(--chart-3))',
    				'4': 'hsl(var(--chart-4))',
    				'5': 'hsl(var(--chart-5))'
    			}
    		},
    		// borderRadius: {
    		// 	lg: 'var(--radius)',
    		// 	md: 'calc(var(--radius) - 2px)',
    		// 	sm: 'calc(var(--radius) - 4px)'
    		// }
    }},
    plugins: [require("tailwindcss-animate")]
};
