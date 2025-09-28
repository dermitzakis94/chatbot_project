def generate_rating_popup(clean_name, primary_color, api_key):
    """
    Απλό rating popup για αξιολόγηση μετά από 2 λεπτά αδράνειας
    """
    return {
        'html': f"""
        <div id="rating-popup-{clean_name}" class="rating-popup-{clean_name}" style="display: none;">
            <div class="rating-content-{clean_name}">
                <h3>Πώς σας φάνηκε;</h3>
                <div class="stars-{clean_name}">
                    <span class="star-{clean_name}" data-rating="1">⭐</span>
                    <span class="star-{clean_name}" data-rating="2">⭐</span>
                    <span class="star-{clean_name}" data-rating="3">⭐</span>
                    <span class="star-{clean_name}" data-rating="4">⭐</span>
                    <span class="star-{clean_name}" data-rating="5">⭐</span>
                </div>
                <button id="rating-skip-{clean_name}">Παράλειψη</button>
                <button id="rating-submit-{clean_name}" disabled>Αποστολή</button>
            </div>
        </div>""",
        
        'css': f"""
        .rating-popup-{clean_name} {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            z-index: 1002;
            font-family: system-ui, sans-serif;
            text-align: center;
        }}
        
        .rating-popup-{clean_name} h3 {{
            margin: 0 0 15px 0;
            font-size: 16px;
            color: #333;
        }}
        
        .stars-{clean_name} {{
            margin: 15px 0;
        }}
        
        .star-{clean_name} {{
            font-size: 24px;
            cursor: pointer;
            opacity: 0.3;
        }}
        
        .star-{clean_name}.active {{
            opacity: 1;
        }}
        
        .rating-popup-{clean_name} button {{
            margin: 10px 5px 0 5px;
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        
        #rating-skip-{clean_name} {{
            background: #f5f5f5;
            color: #666;
        }}
        
        #rating-submit-{clean_name} {{
            background: {primary_color};
            color: white;
        }}
        
        #rating-submit-{clean_name}:disabled {{
            opacity: 0.5;
        }}""",
        
        'js': f"""
        let inactivityTimer = null;
        let currentRating = 0;
        let ratingSubmitted = localStorage.getItem('rating_' + apiKey) === 'true';
        
        const ratingPopup = document.getElementById('rating-popup-{clean_name}');
        const ratingStars = document.querySelectorAll('.star-{clean_name}');
        const ratingSkipBtn = document.getElementById('rating-skip-{clean_name}');
        const ratingSubmitBtn = document.getElementById('rating-submit-{clean_name}');
        
        function startInactivityTimer() {{
            if (ratingSubmitted) return;
            clearTimeout(inactivityTimer);
            inactivityTimer = setTimeout(() => {{
                ratingPopup.style.display = 'block';
            }}, 2 * 60 * 1000);
        }}
        
        function clearInactivityTimer() {{
            clearTimeout(inactivityTimer);
        }}
        
        ratingStars.forEach((star, index) => {{
            star.addEventListener('click', () => {{
                currentRating = index + 1;
                ratingStars.forEach((s, i) => {{
                    s.classList.toggle('active', i < currentRating);
                }});
                ratingSubmitBtn.disabled = false;
            }});
        }});
        
        ratingSkipBtn.addEventListener('click', () => {{
            ratingPopup.style.display = 'none';
            localStorage.setItem('rating_' + apiKey, 'true');
            ratingSubmitted = true;
        }});
        
        ratingSubmitBtn.addEventListener('click', async () => {{
            try {{
                await fetch('http://127.0.0.1:8000/widget-rating', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        api_key: '{api_key}',
                        session_id: sessionId,
                        rating: currentRating
                    }})
                }});
            }} catch (e) {{
                console.log('Rating failed:', e);
            }}
            ratingPopup.style.display = 'none';
            localStorage.setItem('rating_' + apiKey, 'true');
            ratingSubmitted = true;
        }});
        
        closeChat.addEventListener('click', () => {{
            if (!ratingSubmitted && messageHistory.length > 0) {{
                setTimeout(() => ratingPopup.style.display = 'block', 300);
            }}
        }});
        
        const originalAddMessage = addMessage;
        addMessage = function(content, isUser = false) {{
            originalAddMessage.call(this, content, isUser);
            if (isUser) clearInactivityTimer();
            else startInactivityTimer();
        }};"""
    }
