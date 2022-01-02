from flask.helpers import send_file, send_from_directory
from matplotlib.colors import Colormap
from numpy import NaN
from werkzeug.utils import format_string, secure_filename
import os, pandas as pd
import datetime, time
import cv2
import uuid
import shutil
import atexit
import json
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask,after_this_request, session, Response, flash, request, redirect, url_for,render_template

#folder for storing csv file
UPLOAD_FOLDER_WINDOWS='files\\rating'

#allowed file extensions
ALLOWED_EXTENSIONS = {'csv'}
ALLOWED_EXTENSIONS_PROPERTIES = {'json'}


#global variables for storing plot labeling information
title=''
company_label=''
value_label=''

# method for removing generated videos
def clean_up_videos_folder():
    videos_folder="videos"
    videos=[video for video in os.listdir(videos_folder) if video.endswith(".avi")]
    
    for video in videos:
        try:
            os.remove(videos_folder+"\\"+video)
            print("Removed video "+video+" on "+time.strftime("%A, %d. %B %Y %I:%M:%S %p"))

        except OSError:
            print("Couldn'\ delete video "+video+". Reason: "+OSError.strerror)
    
    
#scheduler object for deleting videos every given time
scheduler = BackgroundScheduler()
#delete videos every 15 minutes
scheduler.add_job(func=clean_up_videos_folder, trigger="interval", seconds=60*15)
scheduler.start()

#stop scheduler on app shutdown
atexit.register(lambda: scheduler.shutdown())

#color map "company - color"
company_color_map={}
# list of supported 24 colors
# !!!WARNING!!! only 24 rating objects are supported!
all_colors=['red','green','blue','orange','yellow','gray','black','olive','violet','pink',
            'brown','maroon','orangered','sienna','tan','goldenrod','gold','lawngreen','turquoise','deepskyblue',
            'darkmagenta','indigo','lightsteelblue','darkkhaki','salmon']


app=Flask(__name__)
# set upload folder in config
app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER_WINDOWS

# route for main page
@app.route('/',methods=['GET'])
def home():
    return render_template('home.html')
# route for rating generator page
@app.route('/rating_generator',methods=['GET'])
def rating():
    return render_template('rating.html')

# route for the page after rating generation
# not used right now
# @app.route('/rating_processing',methods=['GET'])
# def rating_processing():
#     return render_template('rating.html')

# route for main processing
@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
    #connect to global variables (see higher)
    global title,company_label,value_label
    if request.method == 'POST':
        # create unical string for video id
        uid=uuid.uuid4()
        
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        properties_file=request.files['properties']
        
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            #print(filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            #print(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # if user has uploaded a properties file then read labeling information from it
            if properties_file and allowed_file_properties(properties_file.filename):
                pr_filename = secure_filename(properties_file.filename)
                properties_file.save(os.path.join(app.config['UPLOAD_FOLDER'], pr_filename))

                pr_file_object = open(os.path.join(app.config['UPLOAD_FOLDER'], pr_filename))
    
                pr_file_data = json.load(pr_file_object)
 
                
                title=pr_file_data['title']
                company_label=pr_file_data['rating_unit']
                value_label=pr_file_data['value']

                pr_file_object.close()
            else:
                # else read information from text input fields
                title=request.form['title']
                company_label=request.form['rating_unit']
                value_label=request.form['value']
                



            # read csv
            df=pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            #read first row of csv to remember the starting date
            first_row=df.loc[0]
            first_date_str=first_row['date']
            current_date=datetime.datetime.strptime(first_date_str,"%d.%m.%Y")
            # this counter is used for image names uniqueness
            counter=1
            x=df.loc[df['date'] == current_date.strftime("%d.%m.%Y")]
            # generate an empty dataframe only with the first date companies' names and zero values
            # it is important to build a "flowing" graph for the first value
            companies=[]
            values=[]
            for index,row in x.iterrows():
                companies.append(row['company'])
                values.append(0)
            old_x=pd.DataFrame(list(zip(companies,values)),columns=['company', 'value'])
            
            # frame_diff keeps the divider on which the difference between two dates will change 
            # and number of frames
            frame_diff=12
            #path for images folder
            path='images-'+str(uid)

            while True:
                x=df.loc[df['date'] == current_date.strftime("%d.%m.%Y")]#'01.01.2010']
                if (x.size==0):
                    break          #stop loop if no more data is available         

                if (old_x is not None):
                    # draw a "flowing" graph if there is a previous dataset 
                    for i in range(frame_diff):
                        companies=[]
                        values=[]

                        for index,row in x.iterrows():
                                new_company=row['company']
                                new_value=row['value']

                                companies.append(new_company)
                                #find the company from the previous date dataset
                                old_row=old_x.loc[old_x['company'] == new_company]
                                if(not old_row.empty):
                                    old_value=old_row['value'].iloc[0]
                                    diff=new_value-old_value
                                    values.append(old_value+(i+1)*(diff/frame_diff))
                                else:
                                    values.append((i+1)*(new_value/frame_diff))
                        # this loop is for case when the row in old dataset does not exist in current one
                        for index,row in old_x.iterrows():
                                old_company=row['company']
                                old_value=row['value']

                                new_row=x.loc[x['company'] == old_company]
                                if(new_row.empty):
                                    diff=old_value
                                    companies.append(old_company)
                                    show_value=old_value-(i+1)*(old_value/frame_diff)
                                    # don't let value go negative
                                    if(show_value<0):
                                        show_value=0
                                    values.append(show_value)
                        # create temporary dataframe and draw it
                        temp_x=pd.DataFrame(list(zip(companies,values)),columns=['company', 'value'])
                        # for the first row take the current row date, else of the previous
                        if(current_date==datetime.datetime.strptime(first_date_str,"%d.%m.%Y")):
                            draw_a_plot_temp(temp_x,counter-1,i+1,path,current_date)
                        else:
                            draw_a_plot_temp(temp_x,counter-1,i+1,path,current_date-datetime.timedelta(days=1))

                        
                # draw a current day data 
                draw_a_plot(x,counter,path,current_date)

                # increment counter and date values, remember current dataframe for the next loop
                counter=counter+1
                current_date=current_date+datetime.timedelta(days=1)
                old_x=x

            # video name from uid
            video_name = str(uid)+'.avi'
            video_path="videos"
            # create videos folder if it does not exist
            if(os.path.exists(video_path)==False):
                os.makedirs(video_path)
            # list all images
            images = [img for img in os.listdir(path) if img.endswith(".jpeg")]
            # get frame heigt and width
            frame = cv2.imread(os.path.join(path, images[0]))
            height, width, layers = frame.shape
            # 7 is fps, the higher ,the faster video goes
            video = cv2.VideoWriter(video_path+'\\'+video_name, 0, 7, (width,height))

            for image in images:
                video.write(cv2.imread(os.path.join(path, image)))

            cv2.destroyAllWindows()
            video.release()

            #cleanup images and files after video generating
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            if properties_file:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], pr_filename))
            shutil.rmtree(path)
            # return video for download
            return send_from_directory(directory=video_path,filename=video_name,as_attachment=True)
             
        if file and allowed_file(file.filename)==False:
            flash('Only CSV files are allowed')
            return redirect(url_for('rating_processing'))

def draw_a_plot_temp(input_x,counter,frame_cnt,path,current_date):
    # sort dataframe by value
    input_x=input_x.sort_values("value")
    # take top 10 rows
    input_x=input_x.head(10)
    for index,row in input_x.iterrows():
        for color in all_colors:
            # give each company a color
            if ( ((row['company'] in company_color_map) == False)  & (find_color_in_dict(color)==1)):
                company_color_map[row['company']]=color
    
    #generate colors tuple for plot
    colors_tuple=generate_colors(input_x)
    ax = input_x.plot(x='company',y='value', kind='barh', figsize=(8, 10),  zorder=2, width=0.45, color=colors_tuple,legend=False)
    ax.set_title(title)
    ax.set_xlabel(value_label)
    ax.set_ylabel(company_label)
    ax.text(0.05, 1.00,current_date.strftime("%d.%m.%Y"), transform=ax.transAxes, fontsize=14,
verticalalignment='bottom')
    
    fig = ax.get_figure()
    
    if(os.path.exists(path)==False):
        os.makedirs(path)
    #save plot as image
    fig.savefig(path+'\\im'+str(counter)+str(frame_cnt).zfill(2)+'.jpeg')


def draw_a_plot(x,counter,path,current_date):
    # sort dataframe by value
    x=x.sort_values("value")
    # take top 10 rows
    x=x.head(10)
    for index,row in x.iterrows():
        for color in all_colors:
            # give each company a color
            if ( ((row['company'] in company_color_map) == False)  & (find_color_in_dict(color)==1)):
                company_color_map[row['company']]=color
    #generate colors tuple for plot
    colors_tuple=generate_colors(x)#['black','yellow','green']
    ax = x.plot(x='company',y='value', kind='barh', figsize=(8, 10),  zorder=2, width=0.45, color=colors_tuple,legend=False)
    ax.set_title(title)
    ax.set_xlabel(value_label)
    ax.set_ylabel(company_label)
    ax.text(0.05, 1.00, current_date.strftime("%d.%m.%Y"), transform=ax.transAxes, fontsize=14,
verticalalignment='bottom')
    fig = ax.get_figure()
    
    if(os.path.exists(path)==False):
        os.makedirs(path)
    #save plot as image
    fig.savefig(path+'\\im'+str(counter)+'.jpeg')
    
            

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def allowed_file_properties(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_PROPERTIES

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