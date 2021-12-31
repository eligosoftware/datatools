from flask.helpers import send_from_directory
from matplotlib.colors import Colormap
from numpy import NaN
from werkzeug.utils import format_string, secure_filename
import os, pandas as pd
import datetime
import cv2
from flask import Flask, session, flash, request, redirect, url_for,render_template


UPLOAD_FOLDER_WINDOWS='files\\rating'
ALLOWED_EXTENSIONS = {'csv'}

company_color_map={}
all_colors=['red','green','blue','orange','yellow','gray','black','olive','violet','pink',
            'brown','maroon','orangered','sienna','tan','goldenrod','gold','lawngreen','turquoise','deepskyblue',
            'darkmagenta','indigo','lightsteelblue','darkkhaki','salmon']


app=Flask(__name__)
app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER_WINDOWS

@app.route('/',methods=['GET'])
def home():
    return render_template('home.html')

@app.route('/rating_generator',methods=['GET'])
def rating():
    return render_template('rating.html')

@app.route('/rating_processing',methods=['GET'])
def rating_processing():
    return render_template('rating.html')

@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        #print(request.url)
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            #print(filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            #print(os.path.join(app.config['UPLOAD_FOLDER'], filename))


            # read csv

            df=pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            #print(df)
            first_row=df.loc[0]
            first_date_str=first_row['date']
            current_date=datetime.datetime.strptime(first_date_str,"%d.%m.%Y")
            #print(current_date)
            counter=1
            old_x=None
            frame_diff=24
            path='images'
            while True:
                #print(current_date.strftime("%d.%m.%Y"))
                x=df.loc[df['date'] == current_date.strftime("%d.%m.%Y")]#'01.01.2010']
                if (x.size==0):
                    break
                # if (old_x is not None):
                #     for i in range(frame_diff):
                #         companies=[]
                #         values=[]

                #         for index,row in x.iterrows():
                #                 new_company=row['company']
                #                 new_value=row['value']

                #                 old_row=old_x.loc[old_x['company'] == new_company]
                #                 old_value=old_row['value']
                #                 diff=new_value-old_value
                #                 companies.append(new_company)
                #                 values.append(old_value+(i+1)*(diff/frame_diff))

                #         for index,row in old_x.iterrows():
                #                 old_company=row['company']
                #                 old_value=row['value']

                #                 new_row=x.loc[x['company'] == old_company]
                #                 if(new_row.empty):
                #                     diff=old_value
                #                     companies.append(old_company)
                #                     show_value=old_value-(i+1)*(old_value/frame_diff)
                #                     if(show_value<0):
                #                         show_value=0
                #                     values.append(show_value)

                #         temp_x=pd.DataFrame( {'company':companies, 'value':values})
                #         draw_a_plot_temp(temp_x,counter,i+1,path,current_date)    

                        
                        
                draw_a_plot(x,counter,path,current_date)


                counter=counter+1
                current_date=current_date+datetime.timedelta(days=1)
                old_x=x

            
            video_name = 'video.avi'

            images = [img for img in os.listdir(path) if img.endswith(".jpeg")]
            frame = cv2.imread(os.path.join(path, images[0]))
            height, width, layers = frame.shape

            video = cv2.VideoWriter(video_name, 0, 1, (width,height))

            for image in images:
                video.write(cv2.imread(os.path.join(path, image)))

            cv2.destroyAllWindows()
            video.release()
            
            return send_from_directory(directory='',filename=video_name,as_attachment=True)
        if file and allowed_file(file.filename)==False:
            flash('Only CSV files are allowed')
            return redirect(url_for('rating_processing'))

def draw_a_plot_temp(x,counter,frame_cnt,path,current_date):
    x=x.sort_values("value")
    x=x.head(10)
    for index,row in x.iterrows():
        for color in all_colors:
            if ( ((row['company'] in company_color_map) == False)  & (find_color_in_dict(color)==1)):
                company_color_map[row['company']]=color
    
    #print(company_color_map)
            


    #print(#['black','yellow','green']
    colors_tuple=generate_colors(x)#['black','yellow','green']
    ax = x.plot(x='company',y='value', kind='barh', figsize=(8, 10),  zorder=2, width=0.45, color=colors_tuple,legend=False)
    ax.set_title("Your Title")
    ax.set_xlabel("Value name")
    ax.text(0.05, 1.00, current_date.strftime("%d.%m.%Y"), transform=ax.transAxes, fontsize=14,
verticalalignment='bottom')
    fig = ax.get_figure()
    
    if(os.path.exists(path)==False):
        os.makedirs(path)
    fig.savefig('images\\im'+str(counter)+str(frame_cnt).zfill(2)+'.jpeg')   
        

def draw_a_plot(x,counter,path,current_date):
    x=x.sort_values("value")
    x=x.head(10)
    for index,row in x.iterrows():
        for color in all_colors:
            if ( ((row['company'] in company_color_map) == False)  & (find_color_in_dict(color)==1)):
                company_color_map[row['company']]=color
    
    #print(company_color_map)
            


    #print(#['black','yellow','green']
    colors_tuple=generate_colors(x)#['black','yellow','green']
    ax = x.plot(x='company',y='value', kind='barh', figsize=(8, 10),  zorder=2, width=0.45, color=colors_tuple,legend=False)
    ax.set_title("Your Title")
    ax.set_xlabel("Value name")
    ax.text(0.05, 1.00, current_date.strftime("%d.%m.%Y"), transform=ax.transAxes, fontsize=14,
verticalalignment='bottom')
    fig = ax.get_figure()
    
    if(os.path.exists(path)==False):
        os.makedirs(path)
    fig.savefig('images\\im'+str(counter)+'.jpeg')
    
            

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_colors(rows_collection):
    colors=[]
    for index,row in rows_collection.iterrows():
        colors.append(company_color_map[row['company']])
    return colors
def find_color_in_dict(search_color):
    for company,color in company_color_map.items():
        if search_color==color:
            return -1
    return 1

if __name__=='__main__':
    app.config['SECRET_KEY']='hBHjvnd32823'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run()