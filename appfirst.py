from flask import Flask, request, render_template, redirect, url_for, flash, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from datetime import datetime

# 初始化Flask應用程式
app = Flask(__name__)

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

   

# 定義出席紀錄的資料庫模型


@app.route('/')
def index():
    return redirect(url_for('items'))

@app.route('/items', methods=['GET'])
def items():
    wardrobe_id = request.args.get('wardrobe_id', 'All')  # 默認顯示所有
    category = request.args.get('category', None)

    query = Item.query
    if wardrobe_id != 'All':
        query = query.filter(Item.wardrobe == wardrobe_id)
    if category:
        query = query.filter(Item.category == category)
    

    items = query.all()
    return render_template('items.html', items=items ,selected_wardrobe=wardrobe_id, selected_category=category)

@app.route('/add_item',methods=['GET','POST'])
def add_item():
    if request.method=='POST':
        name=request.form['name']
        category=request.form['category']
        color=request.form['color']
        wardrobe=request.form['wardrobe']
        photo=request.files['photo']

    
        new_item=Item(
            name = name,
            category = category,
            color = color,
            wardrobe = wardrobe
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


@app.route('/delete_item/<int:item_id>',methods=['POST'])
def delete_item(item_id):
    record=Item.query.get_or_404(item_id)
    if record:
        try:
            db.session.delete(record)
            db.session.commit()
            flash('已刪除','success')
        except Exception as e:
            db.session.rollback()
            flash(f'刪除失敗:{str(e)}','danger')
    else:
        flash('找不到指定紀錄','warning')
    return redirect(url_for('items'))




if __name__=='__main__':
    app.run(debug=True)