from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS
from database import db

router = Router()

class AdminStates(StatesGroup):
    waiting_product_name = State()
    waiting_product_description = State()
    waiting_product_price = State()
    waiting_product_keys = State()
    waiting_delete_id = State()

def main_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton(text="🛍 Каталог товаров", callback_data="catalog")],
        [InlineKeyboardButton(text="📦 Мои покупки", callback_data="my_purchases")],
        [InlineKeyboardButton(text="ℹ️ Информация", callback_data="info")]
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def admin_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product")],
        [InlineKeyboardButton(text="📝 Список товаров", callback_data="admin_list_products")],
        [InlineKeyboardButton(text="❌ Удалить товар", callback_data="admin_delete_product")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def catalog_keyboard(products):
    keyboard = []
    for product in products:
        keyboard.append([InlineKeyboardButton(
            text=f"{product[1]} - {product[3]}₽ (В наличии: {product[4]})",
            callback_data=f"product_{product[0]}"
        )])
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def product_keyboard(product_id):
    keyboard = [
        [InlineKeyboardButton(text="💳 Купить", callback_data=f"buy_{product_id}")],
        [InlineKeyboardButton(text="🔙 К каталогу", callback_data="catalog")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("start"))
async def cmd_start(message: Message):
    db.add_user(message.from_user.id, message.from_user.username)
    await message.answer(
        f"👋 Добро пожаловать, {message.from_user.first_name}!\n\n"
        "🛍 Это магазин цифровых товаров.\n"
        "Выберите нужный раздел:",
        reply_markup=main_keyboard(message.from_user.id)
    )

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏠 Главное меню:\n"
        "Выберите нужный раздел:",
        reply_markup=main_keyboard(callback.from_user.id)
    )
    await callback.answer()

@router.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
    products = db.get_all_products()
    if not products:
        await callback.message.edit_text(
            "😔 Каталог пока пуст",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
            ])
        )
    else:
        await callback.message.edit_text(
            "🛍 Каталог товаров:\n"
            "Выберите товар для просмотра:",
            reply_markup=catalog_keyboard(products)
        )
    await callback.answer()

@router.callback_query(F.data.startswith("product_"))
async def show_product(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = db.get_product(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    text = (
        f"📦 {product[1]}\n\n"
        f"📝 Описание:\n{product[2]}\n\n"
        f"💰 Цена: {product[3]}₽\n"
        f"📊 В наличии: {product[4]} шт."
    )
    
    await callback.message.edit_text(text, reply_markup=product_keyboard(product_id))
    await callback.answer()

@router.callback_query(F.data.startswith("buy_"))
async def buy_product(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = db.get_product(product_id)
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    if product[4] == 0:
        await callback.answer("❌ Товар закончился", show_alert=True)
        return
    
    key = db.get_available_key(product_id)
    
    if key:
        db.mark_key_sold(key[0])
        db.add_purchase(callback.from_user.id, product_id, product[3])
        
        await callback.message.answer(
            f"✅ Покупка успешна!\n\n"
            f"📦 Товар: {product[1]}\n"
            f"💰 Цена: {product[3]}₽\n\n"
            f"🔑 Ваш ключ:\n<code>{key[2]}</code>\n\n"
            f"Спасибо за покупку! 🎉",
            parse_mode="HTML"
        )
        
        await callback.message.edit_text(
            "✅ Покупка завершена!\n"
            "Ключ отправлен вам в личные сообщения.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 В каталог", callback_data="catalog")]
            ])
        )
    else:
        await callback.answer("❌ Ошибка получения ключа", show_alert=True)
    
    await callback.answer()

@router.callback_query(F.data == "my_purchases")
async def show_purchases(callback: CallbackQuery):
    purchases = db.get_user_purchases(callback.from_user.id)
    
    if not purchases:
        text = "📦 У вас пока нет покупок"
    else:
        text = "📦 Ваши покупки:\n\n"
        for purchase in purchases:
            text += f"• {purchase[0]} - {purchase[1]}₽\n  {purchase[2]}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "info")
async def show_info(callback: CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ Информация о магазине:\n\n"
        "🛍 Мы продаем цифровые товары\n"
        "⚡️ Мгновенная выдача после оплаты\n"
        "🔒 Безопасные транзакции\n"
        "💬 Поддержка 24/7\n\n"
        "По всем вопросам: @support",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "admin")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⚙️ Админ-панель\n"
        "Выберите действие:",
        reply_markup=admin_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    total_users, total_purchases, total_revenue = db.get_stats()
    
    text = (
        "📊 Статистика магазина:\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"🛍 Всего покупок: {total_purchases}\n"
        f"💰 Общая выручка: {total_revenue}₽"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "admin_add_product")
async def admin_add_product_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await callback.message.edit_text("➕ Введите название товара:")
    await state.set_state(AdminStates.waiting_product_name)
    await callback.answer()

@router.message(AdminStates.waiting_product_name)
async def admin_add_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📝 Введите описание товара:")
    await state.set_state(AdminStates.waiting_product_description)

@router.message(AdminStates.waiting_product_description)
async def admin_add_product_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("💰 Введите цену товара (только число):")
    await state.set_state(AdminStates.waiting_product_price)

@router.message(AdminStates.waiting_product_price)
async def admin_add_product_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        await state.update_data(price=price)
        
        data = await state.get_data()
        product_id = db.add_product(data['name'], data['description'], price)
        
        await state.update_data(product_id=product_id)
        await message.answer(
            f"✅ Товар создан!\n\n"
            f"Теперь добавьте ключи для товара.\n"
            f"Отправьте ключи (каждый с новой строки):\n"
            f"Или отправьте /skip чтобы добавить позже"
        )
        await state.set_state(AdminStates.waiting_product_keys)
    except ValueError:
        await message.answer("❌ Неверный формат цены. Введите число:")

@router.message(AdminStates.waiting_product_keys)
async def admin_add_product_keys(message: Message, state: FSMContext):
    if message.text == "/skip":
        await message.answer(
            "✅ Товар добавлен без ключей",
            reply_markup=main_keyboard(message.from_user.id)
        )
        await state.clear()
        return
    
    data = await state.get_data()
    product_id = data['product_id']
    
    keys = message.text.strip().split('\n')
    for key in keys:
        if key.strip():
            db.add_product_key(product_id, key.strip())
    
    await message.answer(
        f"✅ Добавлено {len(keys)} ключей для товара",
        reply_markup=main_keyboard(message.from_user.id)
    )
    await state.clear()

@router.callback_query(F.data == "admin_list_products")
async def admin_list_products(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    products = db.get_all_products()
    
    if not products:
        text = "📝 Товаров пока нет"
    else:
        text = "📝 Список товаров:\n\n"
        for product in products:
            text += f"ID: {product[0]}\n{product[1]} - {product[3]}₽\nВ наличии: {product[4]}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "admin_delete_product")
async def admin_delete_product_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    products = db.get_all_products()
    
    if not products:
        await callback.answer("❌ Нет товаров для удаления", show_alert=True)
        return
    
    text = "❌ Введите ID товара для удаления:\n\n"
    for product in products:
        text += f"ID: {product[0]} - {product[1]}\n"
    
    await callback.message.edit_text(text)
    await state.set_state(AdminStates.waiting_delete_id)
    await callback.answer()

@router.message(AdminStates.waiting_delete_id)
async def admin_delete_product_confirm(message: Message, state: FSMContext):
    try:
        product_id = int(message.text)
        product = db.get_product(product_id)
        
        if product:
            db.delete_product(product_id)
            await message.answer(
                f"✅ Товар '{product[1]}' удален",
                reply_markup=main_keyboard(message.from_user.id)
            )
        else:
            await message.answer(
                "❌ Товар с таким ID не найден",
                reply_markup=main_keyboard(message.from_user.id)
            )
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите число:")
