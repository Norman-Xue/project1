from flask import Flask, request, render_template, redirect, url_for, flash, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt, check_password_hash, generate_password_hash
import secrets

# 初始化Flask應用程式
app = Flask(__name__, static_folder='static')

# 設定Flask的秘密金鑰，用於安全的Session管理
app.secret_key = os.urandom(24).hex()

# 設定資料庫連線，這裡使用MySQL資料庫，並使用pymysql作為連接驅動
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@127.0.0.1:3306/project'
# 設定不追蹤資料庫的修改，這有助於提升效能
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 設定上傳檔案的儲存路徑
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 初始化資料庫，這裡使用SQLAlchemy來管理資料庫
db = SQLAlchemy(app)
bcrypt=Bcrypt(app)


login_manger=LoginManager(app)
login_manger.login_view='login'

# 定義學生資料的資料庫模型
class Item(db.Model):
    __tablename__ = 'items'
    # 設定資料表的欄位，對應學生資料
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.Enum('上身', '下身', '連身', '其他'), nullable=False)
    color = db.Column(db.Enum('暖色', '冷色', '黑白', '其他'), nullable=False)
    description = db.Column(db.Text)
    wardrobe = db.Column(db.Enum('A', 'B', 'C'), nullable=False)
    clothes_photo_path = db.Column(db.String(255))
    is_deleted=db.Column(db.Boolean,default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # 建立與 User 模型的關聯
    user = db.relationship('User', back_populates='items')

class User(db.Model,UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)

    items = db.relationship('Item', back_populates='user')



#首頁
@app.route('/')
def index():
    return render_template("index.html")

#使用者物品頁
@app.route('/items', methods=['GET'])
@login_required
def items():
    wardrobe_id = request.args.get('wardrobe_id', 'All')  # 默認顯示所有
    category = request.args.get('category', None)
    show_deleted = request.args.get('show_deleted', 'False') == 'True'  # 判斷是否顯示已刪除的物品

    query = Item.query.filter(Item.user_id == current_user.id)  # 只顯示當前用戶的物品
    if wardrobe_id != 'All':
        query = query.filter(Item.wardrobe == wardrobe_id)
    if category:
        query = query.filter(Item.category == category)
    if not show_deleted:
        query = query.filter(Item.is_deleted == False)  # 只顯示未刪除的物品
    

    items = query.all()
    return render_template('items.html', items=items ,selected_wardrobe=wardrobe_id, selected_category=category)


#使用者新增物品功能
@app.route('/add_item',methods=['GET','POST'])
@login_required
def add_item():
    if request.method=='POST':
        name=request.form['name']
        category=request.form['category']
        color=request.form['color']
        wardrobe=request.form['wardrobe']
        description=request.form['description']
        photo=request.files['photo']

    
        new_item=Item(
            name = name,
            category = category,
            color = color,
            wardrobe = wardrobe,
            description = description,
            user_id=current_user.id
        )
        db.session.add(new_item)
        db.session.commit()
        
        if photo and photo.filename != '':
            extension = photo.filename.rsplit('.', 1)[-1].lower()
            if extension in ['jpg', 'jpeg', 'png']:
                filename = f"{new_item.id}.{extension}"
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                new_item.clothes_photo_path = filename
                db.session.commit()
            else:
                flash('檔案附檔名不合法，只能上傳 jpg、jpeg、png 格式的檔案', 'error')


        flash('物品資料新增成功')
        return redirect('/items')

    return render_template('add_item.html')

#使用者編輯物品
@app.route('/edit_item/<int:item_id>',methods=['GET','POST'])
def edit_item(item_id):
    item=Item.query.get_or_404(item_id)


    if request.method == 'POST':
        item.name = request.form['name']
        item.wardrobe = request.form['wardrobe']
        item.category = request.form['category']
        item.color = request.form['color']
        item.description = request.form['description']
        
     
        if'photo' in request.files:
            photo=request.files['photo']
            if photo and photo.filename !='':
                if'.'in photo.filename:
                    extension=photo.filename.rsplit('.',1)[-1].lower()
                    if extension not in ['jpg','jpeg','png']:
                        flash('上傳檔案格式不正確','danger')
                        return redirect(request.url)
                filename=f"{item.id}.{extension}"

                if item.clothes_photo_path and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'],item.clothes_photo_path)):
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'],item.clothes_photo_path))
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                item.clothes_photo_path=filename
            db.session.commit()
            flash('物品資料已更新','success')
        return redirect(url_for('items'))
    return render_template('edit_item.html',item=item)


#刪除物品
@app.route('/delete_item/<int:item_id>',methods=['POST'])
def delete_item(item_id):
    record=Item.query.get_or_404(item_id)
    if record:
        try:
            record.is_deleted=True
            db.session.commit()
            flash('物品已移至回收箱','success')
        except Exception as e:
            db.session.rollback()
            flash(f'刪除失敗:{str(e)}','danger')
    else:
        flash('找不到指定紀錄','warning')
    return redirect(url_for('items'))

#舊衣回收功能
@app.route('/trash',methods=['GET'])
@login_required
def trash():
    items=Item.query.filter_by(is_deleted=True and Item.user_id == current_user.id).all()
    return render_template('trash.html',items=items)

#還原回收物品功能
@app.route('/restore_item/<int:item_id>',methods=['POST'])
def restore_item(item_id):
    record=Item.query.get_or_404(item_id)
    if record:
        try:
            record.is_deleted=False
            db.session.commit()
            flash('物品以還原','success')
        except Exception as e:
            db.session.rollback()
            flash(f'還原失敗:{str(e)}','danger')
    else:
        flash('找不到指定紀錄','warning')
    return redirect(url_for('trash'))

#永久刪除
@app.route('/realdelete_item/<int:item_id>',methods=['POST'])
def realdelete_item(item_id):
    record=Item.query.get_or_404(item_id)
    if record:
        try:
            db.session.delete(record)
            db.session.commit()
            flash('已永久刪除','success')
        except Exception as e:
            db.session.rollback()
            flash(f'刪除失敗:{str(e)}','danger')
    else:
        flash('找不到指定紀錄','warning')
    return redirect(url_for('items'))



#使用者註冊
@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        username=request.form['username']
        email=request.form['email']
        password=request.form['password']

        existing_user=User.query.filter_by(username=username).first()
        if existing_user:
            flash('使用者名稱已存在','danger')
            return redirect(url_for('register'))
        
        existing_email=User.query.filter_by(email=email).first()
        if existing_email:
            flash('使用者電子郵件已存在','danger')
            return redirect(url_for('register'))
        
        password_hash=bcrypt.generate_password_hash(password).decode('utf-8')


        new_user=User(username=username, email=email,password=password_hash)
        db.session.add(new_user) #資料新增到MYSQL
        db.session.commit()

        flash('成功建立帳號','success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


#使用者登入
@app.route('/login',methods=['Get','POST'])
def login():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']

        user=User.query.filter_by(username=username).first()
        if not user:
            flash('使用者名稱或密碼無效','danger')
            return redirect(url_for('login'))
        
        if not check_password_hash(user.password ,password):
            flash('使用者名稱或密碼無效','danger')
            return redirect(url_for('login'))
        
        login_user(user)

        flash('Login Successful','success')
        return redirect(url_for('items'))
    
    return render_template('login.html')

@login_manger.user_loader
def load_user(user_id):
    user=User.query.get(int(user_id))
    if user:
        print(f'Loaded user:{user.username}')
    return user

#使用者登出
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('你已登出','info')
    return redirect(url_for('index'))

if __name__=='__main__':
    app.run(debug=True)