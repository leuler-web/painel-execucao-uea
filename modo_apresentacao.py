import streamlit.components.v1 as components

def ativar_modo_apresentacao(loop_segundos=15, idle_segundos=45):
    """Injeta JavaScript para alternar abas automaticamente e detectar inatividade."""
    loop_ms = loop_segundos * 1000
    idle_ms = idle_segundos * 1000

    js_code = f"""
    <script>
        const LOOP_INTERVAL = {loop_ms}; 
        const IDLE_TIMEOUT = {idle_ms}; 

        let idleTimer;
        let loopTimer;
        let isLooping = true;
        let currentTabIndex = 0;

        const parentDoc = window.parent.document;

        function getTabs() {{
            return parentDoc.querySelectorAll('button[data-baseweb="tab"]');
        }}

        function nextTab() {{
            if (!isLooping) return;
            const tabs = getTabs();
            if (tabs.length === 0) return;

            currentTabIndex = (currentTabIndex + 1) % tabs.length;
            tabs[currentTabIndex].click();
        }}

        function startLoop() {{
            if (!isLooping) {{
                isLooping = true;
                nextTab(); 
                loopTimer = setInterval(nextTab, LOOP_INTERVAL);
            }}
        }}

        function stopLoop() {{
            isLooping = false;
            clearInterval(loopTimer);
        }}

        function resetIdleTimer() {{
            stopLoop();
            clearTimeout(idleTimer);
            idleTimer = setTimeout(startLoop, IDLE_TIMEOUT);
        }}

        const events = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart'];
        events.forEach(evt => {{
            parentDoc.addEventListener(evt, resetIdleTimer, true);
        }});

        loopTimer = setInterval(nextTab, LOOP_INTERVAL);
    </script>
    """
    
    components.html(js_code, height=0, width=0)