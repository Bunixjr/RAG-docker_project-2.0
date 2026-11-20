import os
# Отключаем проверку обновлений в интернете
os.environ["HF_HUB_OFFLINE"] = "1" 

import ollama
import chromadb
from sentence_transformers import SentenceTransformer
import json
import re

CHROMA_DB_PATH = "chroma_db"
COLLECTION_NAME = "chekhov_texts"
MODEL_NAME = "intfloat/multilingual-e5-small"
LLM_MODEL = "qwen2.5:7b"

def find_context(query: str):
    """Ищет текст в базе (векторный поиск + точный поиск по JSON)"""
    model = SentenceTransformer(MODEL_NAME)
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_collection(name=COLLECTION_NAME)

    # 1. Векторный поиск (без порога, всегда берем 1 кусок)
    query_embedding = model.encode([f"query: {query}"]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=1)
    
    context_texts = []
    best_source_text = "" 
    best_work = ""

    for i in range(len(results['documents'][0])):
        text = results['documents'][0][i]
        meta = results['metadatas'][0][i]
        context_texts.append(f"Произведение: {meta['work']}\nТекст:\n{text}")
        best_source_text = text
        best_work = meta['work']

    # 2. Точный поиск по JSON (Гибрид)
    names = re.findall(r'\b[А-ЯЁ][а-яё]+\b', query)
    target_name = names[1] if len(names) > 1 else None
    
    if target_name:
        try:
            with open(f"{CHROMA_DB_PATH}/chunks.json", "r", encoding="utf-8") as f:
                all_chunks = json.load(f)
            for chunk in all_chunks:
                if target_name in chunk['text']:
                    exact_text = f"!!! ВАЖНЫЙ ФРАГМЕНТ !!!\nПроизведение: {chunk['work']}\nТекст:\n{chunk['text']}"
                    context_texts.insert(0, exact_text)
                    
                    # Умный поиск цитаты (вырезаем нужное предложение)
                    sentences = re.split(r'(?<=[.!?])\s+', chunk['text'])
                    for s in sentences:
                        if target_name in s:
                            clean_sentence = " ".join(s.split())
                            best_source_text = clean_sentence
                            best_work = chunk['work']
                            break
                    break
        except FileNotFoundError:
            print("  ⚠️ Файл chunks.json не найден.")

    return "\n\n---\n\n".join(context_texts), best_source_text, best_work

def ask_llm(query: str):
    # 1. Очистка от спецсимволов (защита от Backspace)
    query = re.sub(r'[^а-яА-Яa-zA-Z0-9\s]', '', query)
    query = " ".join(query.split())
    
    print(f"\n🔎 Вопрос: '{query}'")

    # 2. Умный фильтр по стоп-словам
    bad_topics = ["погода", "политика", "футбол", "спорт", "новости", "курс", "доллар", "евро", "программирование", "код", "питон", "математика", "уравнение"]
    
    if any(topic in query.lower() for topic in bad_topics):
        print("\n💬 ОТВЕТ НЕЙРОСЕТИ:")
        print("-" * 50)
        print("Извините, я могу отвечать только по текстам А. П. Чехова. Я не владею информацией о погоде, политике или других темах, не связанных с литературой.")
        print("-" * 50)
        return 

    print("  [1/4] Загрузка модели для поиска (e5) и базы ChromaDB...")
    context, source_text, source_work = find_context(query) 
    print(f"  [2/4] Контекст найден! (Размер: {len(context)} символов).")
    
    # 3. Промпт для нейросети
    prompt = f"""Ты — литературный помощник по текстам А. П. Чехова. 
Твоя задача — отвечать на вопросы, используя ТОЛЬКО предоставленный текст.

ПРАВИЛА:
1. Если вопрос касается литературы, персонажей или событий из текста — ответь кратко и точно.
2. Если вопрос НЕ относится к литературе, но ты уже видишь этот текст — напиши ровно фразу: "В предоставленных отрывках нет ответа."
3. Не выдумывай факты.

ТЕКСТ:
{context}

ВОПРОС: {query}
ОТВЕТ:"""

    print("  [3/4] Отправка запроса в Ollama (модель qwen2.5:7b)...")
    print("        ⏳ Пожалуйста, подождите. Генерация ответа...")
    
    try:
        response = ollama.chat(
            model=LLM_MODEL, 
            messages=[{'role': 'user', 'content': prompt}],
            options={'keep_alive': '5m'}
        )
        print("  [4/4] Ответ получен!\n")
        
        answer_text = response['message']['content']
        print("💬 ОТВЕТ НЕЙРОСЕТИ:")
        print("-" * 50)
        print(answer_text)
        print("-" * 50)
        
        # 4. Вывод цитаты (ТОЛЬКО если есть ответ)
        # Проверяем, не сказала ли нейросеть, что ответа нет
        answer_lower = answer_text.lower()
        is_no_answer = any(phrase in answer_lower for phrase in [
            "нет ответа", "не знаю", "не сказано", "нет информации", "не могу ответить", "извините"
        ])
        
        if not is_no_answer and source_text:
            print("\n📚 ИСТОЧНИК И ЦИТАТА-ДОКАЗАТЕЛЬСТВО:")
            print(f"Произведение: {source_work}")
            print(f"Цитата: «{source_text.strip()}»") 
            print("-" * 50)

    except Exception as e:
        print(f"\n❌ ОШИБКА при работе с Ollama: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("📚 Литературный RAG-помощник по текстам А. П. Чехова")
    print("=" * 50)
    print("Введите 'выход' или 'exit', чтобы завершить работу.\n")
    
    while True:
        user_query = input("👉 Ваш вопрос: ")
        
        if user_query.lower() in ['выход', 'exit', 'quit']:
            print("До свидания!")
            break
            
        if not user_query.strip():
            continue
            
        ask_llm(user_query)
        print("\n" + "-" * 50 + "\n")