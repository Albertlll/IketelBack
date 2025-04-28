from .server import sio 

games = {}

@sio.event
async def connect(sid, environ):
    print(f"Клиент подключился: {sid}")

@sio.event
async def host_start(sid, adventure_id):
    games[adventure_id] = {
        'host': sid,
        'players': {},
        'status': 'waiting'
    }
    await sio.emit('game_created', {'adventure_id': adventure_id}, to=sid)

@sio.event
async def player_join(sid, adventure_id, username):
    if adventure_id not in games:
        return
    
    games[adventure_id]['players'][sid] = {
        'name': username,
        'score': 0
    }
    
    await sio.enter_room(sid, adventure_id)
    await sio.emit('player_joined', {'sid': sid, 'username': username}, room=adventure_id)

@sio.event
async def start_game(sid, adventure_id, game_data):
    if games.get(adventure_id, {}).get('host') != sid:
        return
    
    games[adventure_id]['status'] = 'playing'
    await sio.emit('game_started', game_data, room=adventure_id)



@sio.event
async def get_current_step(sid):
    """Получение текущего шага для игрока"""
    progress = db.query(PlayerProgress).filter_by(socket_id=sid).first()
    if not progress:
        return
    
    step = db.query(AdventureStep)\
           .filter_by(
               session_id=progress.session_id,
               step_number=progress.current_step + 1
           )\
           .first()
    
    await sio.emit('current_step', {
        'step': step_to_dict(step),
        'progress': {
            'current': progress.current_step + 1,
            'total': db.query(AdventureStep)
                     .filter_by(session_id=progress.session_id)
                     .count()
        }
    }, to=sid)

@sio.event
async def submit_step_answer(sid, answer):
    """Обработка ответа"""
    progress = db.query(PlayerProgress).filter_by(socket_id=sid).first()
    if not progress:
        return
    
    step = db.query(AdventureStep)\
           .filter_by(
               session_id=progress.session_id,
               step_number=progress.current_step + 1
           )\
           .first()
    
    # Проверка ответа
    is_correct = False
    if step.type == "word_translation":
        is_correct = answer.lower() == step.content["correct"].lower()
    elif step.type == "multiple_choice":
        is_correct = int(answer) == step.content["correct_id"]
    
    # Обновление прогресса
    progress.completed_steps.append({
        'step_id': step.id,
        'is_correct': is_correct,
        'timestamp': datetime.utcnow()
    })
    
    if progress.current_step < db.query(AdventureStep).filter_by(session_id=progress.session_id).count() - 1:
        progress.current_step += 1
    
    db.commit()
    
    # Отправка результата
    await sio.emit('step_result', {
        'is_correct': is_correct,
        'correct_answer': step.content["correct"] if step.type == "word_translation" 
                         else step.content["correct_id"]
    }, to=sid)