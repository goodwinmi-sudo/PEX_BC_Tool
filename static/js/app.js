let currentStep = 0;
let simulationSteps = [];
let availablePersonas = [];
let activePersonas = [];

const fallbackSteps = [
    { title: "Vision Digest & Mapping", label: "Extracting Layout...", btn: "Map original Slides", role: "UX Audit", message: "Layout mapped perfectly. Preserving visual schema.", logs: ["[INFO] Initializing Multimodal Agent", "[INFO] Loading PPTX binary", "[SUCCESS] 12 slides detected", "[AUDIT] Extracting Hex #4285F4", "[AUDIT] Found Google Sans Font family"] },
    { title: "Track Determination", label: "Classifying Deal...", btn: "Identify Track", role: "Infrastructure", message: "Infrastructure requirements verified.", logs: ["[INFO] NLP classification active", "[INFO] Keywords detected: 'Uncapped', 'OEM'", "[AUDIT] Route set: BUSINESS_COUNCIL", "[SUCCESS] Track confirmed"] },
    { title: "Approver OKR Fetch", label: "Loading motivations...", btn: "Fetch Persona Intel", role: "Quality Excellence", message: "Current OKRs for approvers loaded.", logs: ["[INFO] Connecting to internal Moma DB", "[INFO] Fetching 2026 OKRs", "[SUCCESS] Loaded specific liability thresholds"] },
    { title: "BC Simulation Loop #1", label: "Tearing down V1...", btn: "Run Simulation", role: "Product Vision", message: "Liability gaps identified in uncapped device scopes.", logs: ["[INFO] Spawning BC Sim Instance", "[INFO] Adversarial reasoning active", "[CRITICAL] Detected gap in phrase: Indemnification Clause"] },
    { title: "Hardening V2 Package", label: "Applying mitigations...", btn: "Generate V2", role: "Quality Excellence", message: "Applied Unit Caps and OEM Pass-through terms.", logs: ["[INFO] Applying approved redlines", "[INFO] Hardening terms", "[SUCCESS] V2 generated with 3 risk-neutralizing terms"] },
    { title: "Visual Polish Audit", label: "Auditing Layout...", btn: "Run Vision Audit", role: "UX Audit", message: "No text overflow detected. Vision cleared for render.", logs: ["[INFO] Running Geometry Reinforcement", "[INFO] Slide #2 rendering...", "[INFO] Slide #5 rendering...", "[SUCCESS] 0 Text overflows detected"] },
    { title: "Pre-Mortem", label: "Final Stress Test...", btn: "Perform Stress Test", role: "Infrastructure", message: "Approval granted. Pre-mortem reveals 18mo failure mode.", logs: ["[INFO] Engaging Executive Pre-Mortem", "[INFO] Hypothetical failure: 2027 exit", "[ADVICE] Add fallback clause for liability transfer"] },
    { title: "Final Payload Ready", label: "Generating Gem Payload...", btn: "View Results", role: "Product Vision", message: "Ready for launch. All approvers sign off.", logs: ["[INFO] Finalizing Gemini Gem Payload", "[INFO] Formatting presentation link", "[SUCCESS] Package 100% verified"] }
];

document.addEventListener('DOMContentLoaded', async () => {
    // Load personas.json dynamically
    try {
        const response = await fetch('/api/personas');
        availablePersonas = await response.json();
        
        const orgSelect = document.getElementById('org-select');
        orgSelect.addEventListener('change', updatePersonasUI);
        
        // Initial load
        updatePersonasUI();
    } catch (e) {
        console.error("Failed to fetch personas", e);
    }
});

function getInitials(name) {
    if(!name) return 'X';
    return name.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase();
}

function getGradient(name) {
    const chars = name.split('');
    const colors = ['bg-blue-600', 'bg-pink-600', 'bg-emerald-600', 'bg-purple-600', 'bg-amber-600', 'bg-cyan-600', 'bg-indigo-600'];
    const idx = chars.reduce((sum, c) => sum + c.charCodeAt(0), 0) % colors.length;
    return colors[idx];
}

function updatePersonasUI() {
    const orgSelect = document.getElementById('org-select');
    const selectedOrg = orgSelect.value;
    
    // Filter personas based on Org. 
    // Usually, tools like this have an approval matrix. We'll find all the people for this Org.
    activePersonas = availablePersonas.filter(p => p.org === selectedOrg);
    
    // If empty, fallback to some global approvers
    if (activePersonas.length === 0) {
        activePersonas = availablePersonas.slice(0, 3);
    }

    // Determine the track dynamically from the personas found
    const track = activePersonas[0]?.track || 'Standard';
    document.getElementById('active-track').innerText = track;

    const board = document.getElementById('board-insights');
    board.innerHTML = '';
    
    activePersonas.forEach((p, index) => {
        const color = getGradient(p.name);
        const card = document.createElement('div');
        // Map persona roles to step roles for visual linkage in simulation
        const roles = ["UX Audit", "Infrastructure", "Quality Excellence", "Product Vision"];
        p.assignedRole = roles[index % roles.length];

        card.className = `persona-card flex items-start space-x-3 opacity-40 transition-all duration-500 p-3 rounded-2xl border border-transparent hover:border-white/10 hover:bg-white/5`;
        card.id = `persona-${index}`;
        card.onclick = () => openPersona(index);
        
        // Extract a short redline preview from the persona description
        const redlineStr = p.persona || "Standard compliance validation.";

        card.innerHTML = `
            <div class="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center font-bold text-xs ring-1 ring-white/10 ${color}">${getInitials(p.name)}</div>
            <div class="text-sm">
                <p class="font-bold text-slate-300">${p.name}</p>
                <p class="text-slate-500 text-[10px] mt-1 italic leading-tight">${p.okrs ? p.okrs.substring(0,40)+'...' : 'Loading OKRs...'}</p>
            </div>
        `;
        board.appendChild(card);
    });
}

function openPersona(index) {
    const data = activePersonas[index];
    const color = getGradient(data.name);
    
    document.getElementById('modal-title').innerText = data.name;
    document.getElementById('modal-role').innerText = `${data.org} | ${data.track}`;
    document.getElementById('modal-icon').innerText = getInitials(data.name);
    document.getElementById('modal-icon').className = `w-12 h-12 rounded-2xl flex items-center justify-center font-bold text-lg text-white shadow-lg ${color}`;
    
    let okrHtml = `<div class='mb-4 font-bold text-emerald-400 border-b border-white/10 pb-2 flex items-center'><svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>${data.okrs || 'N/A'}</div>`;
    okrHtml += `<div class='mb-1'>${data.persona}</div>`;
    
    if (data.refinements && data.refinements.length > 0) {
        okrHtml += `<div class='mt-4 font-bold text-slate-300 mb-2'>Previous Refinements:</div>`;
        data.refinements.forEach(r => {
            okrHtml += `<div class='mb-1 text-slate-500 flex items-start'><span class="text-blue-500 mr-2">↳</span> ${r}</div>`;
        });
    }
    
    document.getElementById('modal-redlines').innerHTML = okrHtml;
    document.getElementById('persona-modal').classList.remove('hidden');
    document.getElementById('persona-modal').classList.add('flex');
}

function closeModal() {
    document.getElementById('persona-modal').classList.add('hidden');
    document.getElementById('persona-modal').classList.remove('flex');
}

async function startSim(option) {
    document.getElementById('welcome-state').classList.add('hidden');
    document.getElementById('sim-runner').classList.remove('hidden');
    
    simulationSteps = fallbackSteps; // In a full app, this might come from the server
    updateSimUI();
}

async function nextStep() {
    if (currentStep < simulationSteps.length - 1) {
        currentStep++;
        updateSimUI();
        
        // Fire async call to server if needed
        try {
            await fetch('/api/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ step: currentStep, org: document.getElementById('org-select').value })
            });
            // We don't block UI on response to keep performance extremely snappy
        } catch(e) { }
    } else {
        showFinalPackage();
    }
}

function showFinalPackage() {
     document.getElementById('sim-title').innerText = "Simulation Finalized";
     document.getElementById('step-display-container').innerHTML = `
        <div class="space-y-6 launch-anim flex flex-col items-center text-center justify-center">
            <div class="w-20 h-20 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto text-emerald-400 mb-4 ring-2 ring-emerald-500/30">
                <svg class="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg>
            </div>
            <h2 class="text-3xl font-bold">Hardened Package Ready</h2>
            <p class="text-slate-400 max-w-md mx-auto leading-relaxed">Your V3 deck has been hardened with specific approvals and passed all vision audits.</p>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8">
                <a href="#" class="flex items-center justify-center space-x-2 bg-white/5 hover:bg-white/10 p-4 rounded-2xl border border-white/10 transition">
                    <svg class="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zM6 4h7v5h5v11H6V4z"/></svg>
                    <span>Final V3 Slides</span>
                </a>
                <button onclick="copyPayload()" class="flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-700 p-4 rounded-2xl transition shadow-lg shadow-blue-500/20">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path></svg>
                    <span>Copy Gem Payload</span>
                </button>
            </div>
            
            <p class="text-[10px] mono text-slate-600 mt-8 uppercase tracking-widest">Digital Signature: VERIFIED BY BC_BOT_v10.1</p>
        </div>
     `;
     document.getElementById('next-btn').innerHTML = "Reset for New Deal";
     document.getElementById('next-btn').onclick = () => window.location.reload();
}

function copyPayload() {
    alert("Gemini War Room Payload copied to clipboard!");
}

function updateSimUI() {
    const step = simulationSteps[currentStep];
    document.getElementById('sim-title').innerText = step.title;
    document.getElementById('step-counter').innerText = `Step ${currentStep + 1} / ${simulationSteps.length}`;
    document.getElementById('next-btn').innerText = step.btn + " →";
    document.getElementById('loader-text').innerText = step.label;
    
    // Update dots
    const nodes = document.querySelectorAll('.step-node');
    nodes.forEach((node, idx) => {
        if (idx < currentStep) node.className = "step-node w-8 h-8 rounded-full step-complete flex items-center justify-center font-bold text-sm border-2";
        else if (idx === currentStep) node.className = "step-node w-8 h-8 rounded-full glass step-active flex items-center justify-center font-bold text-sm border-2 shadow-lg shadow-blue-500/20";
        else node.className = "step-node w-8 h-8 rounded-full glass flex items-center justify-center font-bold text-sm border-2 border-slate-700";
    });

    // Determine which dynamic persona matches the role for this step
    let matchedPersonaIndex = -1;
    for(let i=0; i<activePersonas.length; i++) {
        if (activePersonas[i].assignedRole === step.role) {
            matchedPersonaIndex = i;
            break;
        }
    }
    // Fallback to first persona if no role match
    if (matchedPersonaIndex === -1 && activePersonas.length > 0) matchedPersonaIndex = 0;

    // Pulse the sidebar card
    document.querySelectorAll('.persona-card').forEach(c => c.classList.remove('opacity-100', 'ring-1', 'ring-blue-500/50', 'bg-blue-500/10'));
    
    if (matchedPersonaIndex !== -1) {
        const pCard = document.getElementById(`persona-${matchedPersonaIndex}`);
        if(pCard) {
            pCard.classList.remove('opacity-40');
            pCard.classList.add('opacity-100', 'ring-1', 'ring-blue-500/50', 'bg-blue-500/10');
            pCard.querySelector('p:last-child').innerText = step.message;
            pCard.querySelector('p:last-child').classList.remove('text-slate-500');
            pCard.querySelector('p:last-child').classList.add('text-blue-400', 'not-italic');
        }
    }

    // Prepare content area
    document.getElementById('loader').classList.remove('hidden');
    document.getElementById('step-display').classList.add('hidden');
    
    // Stream Logs UI
    const stream = document.getElementById('log-stream');
    stream.innerHTML = '';
    
    // Performance improvement: using requestAnimationFrame for smooth drawing instead of timeout blocking
    let logIdx = 0;
    
    // Calculate speed dynamically based on length of logs so users don't wait long
    const durationMs = 600; 
    const intervalMs = Math.max(50, durationMs / (step.logs.length || 1));

    const logTimer = setInterval(() => {
        if (logIdx < step.logs.length) {
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerText = step.logs[logIdx];
            stream.appendChild(entry);
            stream.scrollTop = stream.scrollHeight;
            logIdx++;
        } else {
            clearInterval(logTimer);
            showResult(step, matchedPersonaIndex);
        }
    }, intervalMs);
}

function showResult(step, personaIdx) {
    document.getElementById('loader').classList.add('hidden');
    
    const display = document.getElementById('step-display');
    display.classList.remove('hidden');
    
    let personaName = "System";
    if (personaIdx !== -1 && activePersonas[personaIdx]) {
        personaName = activePersonas[personaIdx].name;
    }
    
    display.innerHTML = `
        <div class="launch-anim">
            <div class="flex items-center justify-center space-x-3 text-emerald-400 mb-8">
                <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
                <span class="text-sm font-mono uppercase tracking-widest">Logic Node Cleared</span>
            </div>
            <p class="text-3xl font-bold text-slate-100 mb-4">${step.label}</p>
            <p class="text-slate-400 text-lg"><strong>${personaName}</strong> (${step.role}) has verified this phase.</p>
        </div>
    `;
}
