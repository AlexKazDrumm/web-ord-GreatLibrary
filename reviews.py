from flask import Blueprint, render_template, request, redirect, flash, url_for
from models import db, Book, Review, User
from flask_login import current_user, login_required
from bleach import clean
from flask_paginate import Pagination, get_page_args
import markdown2
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc

bp = Blueprint('reviews', __name__)


@bp.route('/add_review/<int:book_id>', methods=['GET', 'POST'])
@login_required
def add_review(book_id):
    try:
        book = Book.query.get(book_id)
        existing_review = Review.query.filter_by(book_id=book_id, user_id=current_user.id).first()

        if not current_user.is_authenticated:
            flash("Для выполнения данного действия необходимо пройти процедуру аутентификации", 'error')
            return redirect(url_for('auth.login'))

        if existing_review:
            # Если пользователь уже написал рецензию на данную книгу,
            # отображаем его рецензию
            return redirect(url_for('reviews.my_reviews'))

        if request.method == 'POST':
            rating = int(request.form['rating'])
            text = clean(request.form['comment'], tags=[], attributes={}, protocols=[], strip=True)

            review = Review(book_id=book_id, user_id=current_user.id, rating=rating, text=text, status_id=1)
            db.session.add(review)
            db.session.commit()

            flash('Рецензия успешно добавлена', 'success')
            return redirect(f'/book/{book_id}')

        return render_template('reviews/add_review.html', book=book)
    except SQLAlchemyError:
        flash('Не удалось добавить рецензию', 'error')
        return redirect(url_for('library.view_book', book_id=book_id))

@bp.route('/my_reviews')
@login_required
def my_reviews():
    if not current_user.is_authenticated:
        flash("Для выполнения данного действия необходимо пройти процедуру аутентификации", 'error')
        return redirect(url_for('auth.login'))

    try:
        reviews = Review.query.filter_by(user_id=current_user.id).all()
        for review in reviews:
            book = Book.query.get(review.book_id)
            review.book_title = book.title
            review.book_author = book.author
            review.book_cover = book.cover.filename
            review.text = markdown2.markdown(review.text, extras=['fenced-code-blocks', 'cuddled-lists', 'metadata', 'tables', 'spoiler'])

        return render_template('reviews/my_reviews.html', reviews=reviews)
    except SQLAlchemyError:
        flash('Произошла ошибка базы данных', 'error')
        return redirect(url_for('reviews.my_reviews'))


@bp.route('/moderate')
@login_required
def moderate_reviews():
    if not current_user.is_authenticated:
        flash("Для выполнения данного действия необходимо пройти процедуру аутентификации", 'error')
        return redirect(url_for('auth.login'))

    if current_user.role_id > 2:
        flash("У вас недостаточно прав для выполнения данного действия", 'error')
        return redirect(url_for('library.index'))

    try:
        page = request.args.get('page', 1, type=int)
        per_page = 12

        reviews_pagination = Review.query.filter_by(status_id=1).order_by(desc(Review.date_added)) \
            .paginate(page=page, per_page=per_page, error_out=False)
        reviews = reviews_pagination.items


        for review in reviews:
            user = User.query.get(review.user_id)
            book = Book.query.get(review.book_id)
            review.first_name = user.first_name
            review.book_title = book.title
            review.added_date = review.date_added.strftime('%d.%m.%Y %H:%M')

        total_reviews = Review.query.filter_by(status_id=1).count()

        return render_template('reviews/moderate.html', reviews=reviews, pagination=reviews_pagination)
    except SQLAlchemyError:
        flash('Произошла ошибка базы данных', 'error')
        return redirect(url_for('reviews.moderate_reviews'))


@bp.route('/review/<int:review_id>', methods=['GET', 'POST'])
@login_required
def review(review_id):
    if not current_user.is_authenticated:
        flash("Для выполнения данного действия необходимо пройти процедуру аутентификации", 'error')
        return redirect(url_for('auth.login'))

    if current_user.role_id > 2:
        flash("У вас недостаточно прав для выполнения данного действия", 'error')
        return redirect(url_for('library.index'))

    try:
        review = Review.query.get(review_id)
        review.text = markdown2.markdown(review.text, extras=['fenced-code-blocks', 'cuddled-lists', 'metadata', 'tables', 'spoiler'])
        user = User.query.get(review.user_id)
        book = Book.query.get(review.book_id)

        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'approve':
                review.status_id = 2  # Устанавливаем статус "Одобрено"
                db.session.commit()
                flash('Рецензия одобрена', 'success')
            elif action == 'reject':
                review.status_id = 3  # Устанавливаем статус "Отклонено"
                db.session.commit()
                flash('Рецензия отклонена', 'success')
            return redirect(url_for('reviews.moderate_reviews'))

        return render_template('reviews/review.html', review=review, user=user, book=book)
    except SQLAlchemyError:
        flash('Произошла ошибка базы данных', 'error')
        return redirect(url_for('reviews.review', review_id=review_id))