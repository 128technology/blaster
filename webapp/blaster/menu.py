from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

bp = Blueprint('menu', __name__)

@bp.route('/')
def home():
    return render_template('menu.html')
