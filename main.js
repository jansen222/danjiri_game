// SideRunner Web - Main JavaScript Entry Point

const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const loadingOverlay = document.getElementById('loading-overlay');
const loadingText = document.getElementById('loading-text');

// Input State
const inputState = {
    keys_pressed: new Set(), // Keys pressed THIS frame
    keys_down: new Set(),    // Keys currently held down
    mouse: { x: 0, y: 0, clicked: false }
};

// Key Mapping handling
window.addEventListener('keydown', (e) => {
    // Prevent default scrolling for game keys
    if (['Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code)) {
        e.preventDefault();
    }

    if (!inputState.keys_down.has(e.code)) {
        inputState.keys_pressed.add(e.code);
    }
    inputState.keys_down.add(e.code);
});

window.addEventListener('keyup', (e) => {
    inputState.keys_down.delete(e.code);
});

canvas.addEventListener('mousedown', (e) => {
    inputState.mouse.clicked = true;
});


canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    inputState.mouse.x = (e.clientX - rect.left) * scaleX;
    inputState.mouse.y = (e.clientY - rect.top) * scaleY;
});

// Mobile Control Logic
document.querySelectorAll('.control-btn').forEach(btn => {
    const key = btn.dataset.key;

    const press = (e) => {
        // e.preventDefault(); // Prevent scrolling/zooming but allow click for some
        if (e.cancelable) e.preventDefault();

        if (!inputState.keys_down.has(key)) {
            inputState.keys_pressed.add(key);
        }
        inputState.keys_down.add(key);
        btn.classList.add('active');

        // Vibration feedback (if supported)
        if (navigator.vibrate) navigator.vibrate(10);
    };

    const release = (e) => {
        if (e.cancelable) e.preventDefault();
        inputState.keys_down.delete(key);
        btn.classList.remove('active');
    };

    btn.addEventListener('touchstart', press, { passive: false });
    btn.addEventListener('touchend', release, { passive: false });
    // Also support mouse for testing on desktop
    btn.addEventListener('mousedown', press);
    btn.addEventListener('mouseup', release);
    btn.addEventListener('mouseleave', release);
    btn.addEventListener('contextmenu', e => e.preventDefault());
});



let pyodide = null;
let pyGameInstance = null;
let lastTime = 0;

async function init() {
    try {
        loadingText.innerText = "Loading Pyodide...";
        pyodide = await loadPyodide();

        loadingText.innerText = "Loading Game Scripts...";

        // Fetch game.py content (with cache busting)
        const response = await fetch('game.py?t=' + Date.now());
        if (!response.ok) throw new Error("Failed to load game.py");
        const gameScript = await response.text();

        // Write game.py to Pyodide's virtual filesystem
        pyodide.FS.writeFile("game.py", gameScript);

        loadingText.innerText = "Initializing Game...";

        // Load the script and create game instance
        await pyodide.runPythonAsync(`
import sys
sys.path.append('.')
from game import Game
import js

# Get canvas from DOM explicitly
canvas_el = js.document.getElementById("gameCanvas")

# Create global game instance
game_instance = Game(canvas_el.width, canvas_el.height)
        `);

        // Get reference to the game instance
        pyGameInstance = pyodide.globals.get('game_instance');

        // Hide loading screen
        loadingOverlay.style.opacity = '0';
        setTimeout(() => {
            loadingOverlay.style.display = 'none';
        }, 500);

        // Start Game Loop
        requestAnimationFrame(gameLoop);

    } catch (err) {
        console.error("Initialization Failed:", err);
        loadingText.innerText = "Error: " + err.message;
        loadingText.style.color = "#ff5555";
        loadingText.style.fontSize = "16px";
    }
}

function gameLoop(timestamp) {
    if (!lastTime) lastTime = timestamp;
    let dt = (timestamp - lastTime) / 1000; // Delta time in seconds
    lastTime = timestamp;

    // Clamp dt to prevent physics explosions (max 0.1s)
    if (isNaN(dt) || dt < 0) dt = 0.016;
    if (dt > 0.1) dt = 0.1;

    try {
        // Convert JS input sets to Python list/set friendly format if needed, 
        // or just pass them as proxies. Pyodide handles proxies well.
        // For performance, we might want to simplify simple lists.

        // Prepare input data for Python
        // We pass: { keys_pressed: list, keys_down: list, mouse: dict }
        const inputData = {
            keys_pressed: Array.from(inputState.keys_pressed),
            keys_down: Array.from(inputState.keys_down),
            mouse: inputState.mouse
        };

        // Update Game
        pyGameInstance.update(dt, inputData);

        // Draw Game
        // We pass the canvas context to Python to draw on
        pyGameInstance.draw(ctx);

        // Reset per-frame input flags
        inputState.keys_pressed.clear();
        inputState.mouse.clicked = false;

    } catch (err) {
        console.error("Game Loop Error:", err);
        // Stop loop on error to prevent spam
        return;
    }

    requestAnimationFrame(gameLoop);
}

// Start initialization
init();
