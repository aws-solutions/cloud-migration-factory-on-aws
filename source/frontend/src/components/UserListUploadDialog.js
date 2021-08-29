import React, { Component } from "react";

export default class UserListUploadDialog extends Component {
  constructor(props) {
    super(props);

    this.state = {
      showDialog: this.props.showDialog,
      selectedFile: null,
      uploadRunning: this.props.uploadRunning,
      uploadProgress: this.props.uploadProgress,
      uploadErrors: this.props.uploadErrors
    };
  }

  componentWillReceiveProps(nextProps){
    this.setState({
      showDialog: nextProps.showDialog,
      uploadRunning: nextProps.uploadRunning,
      uploadProgress: nextProps.uploadProgress,
      uploadErrors: nextProps.uploadErrors
    });
  }

  convertCsvToJson(csv){
    var lines=csv.split("\n");
    var result = [];
    var headers=lines[0].trim().split(",");

    for(var i=1;i<lines.length;i++) {
      var obj = {};
      var currentline = lines[i].trim().split(",");
      for(var j=0;j<headers.length;j++) {
        if (currentline[j].charAt(0) === '[' && currentline[j].charAt(currentline[j].length - 1) === ']')
        {
          var arr_str = []
          arr_str = currentline[j].slice(1,currentline[j].length-1).split(';')
        obj[headers[j]] = arr_str
        }
        else {
        obj[headers[j]] = currentline[j];
        }
      }
      result.push(obj);
    }
    return result;
  }

  onClickCancelDialog = event => {
    if (!(this.state.uploadRunning === 'yes')) {
      this.props.closeDialog();
    }
  }

  onClickUpload = event => {

    let fileReader = new FileReader();

    const handleFileRead = (e) => {
      const content = fileReader.result;
      const jsonContent = this.convertCsvToJson(content)
      this.props.processUpload(jsonContent)
    }

    if (this.state.selectedFile !== null){
      fileReader.onloadend = handleFileRead;
      fileReader.readAsText(this.state.selectedFile, "UTF-8");
    }
  }

  onChangeSelectedFile = event => {
    this.setState({selectedFile: event.target.files[0]})
  }


  render() {
    let styles = this.state.showDialog
      ? { display: "block" }
      : { display: "none" };
    return (
      <div>

        {this.state.showDialog &&
          <div>
            <div className="block-events-full"> </div>
            <div className="modal fade show" data-backdrop="static" style={styles} id="ModalCenter" tabIndex="-1" role="dialog" aria-labelledby="ModalCenterTitle" aria-hidden="true">
              <div className="modal-dialog modal-dialog-centered" role="document">
                <div className="modal-content">
                  <div className="modal-header">
                    <h5 className="modal-title" id="ModalLongTitle">
                    <div className="pb-4">
                            <b>File upload </b>
                    </div>
                    </h5>
                    <span onClick={this.onClickCancelDialog} className="onhover float-right">
                        <button type="button" className="close" data-dismiss="modal" aria-label="Close">&times;
                        </button>
                    </span>
                  </div>
                  <div className="modal-body">
                     <div className="pt-1 pl-2" style={{height:"200px"}}>

                        { this.state.uploadRunning !== 'no'?
                          <div>
                            <div className="pb-3">Upload running, do not close window while upload is in progress.</div>
                            <div className="pb-1">Progress:</div>
                            <div className="progress mr-2">
                              <div className="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" aria-valuenow="75" aria-valuemin="0" aria-valuemax="100" style={{width: this.state.uploadProgress+"%"}}></div>
                            </div>

                            {this.state.uploadRunning === 'complete' &&
                            <div className="pt-2">
                            Upload completed with {this.state.uploadErrors} errors.
                            To view complete upload log click here.
                            </div>
                            }
                          </div>
                        :
                          <div>
                            <div>Select csv to upload:</div>
                            <input className="mx-2 my-2 mb-3" type="file" accept=".csv" onChange={this.onChangeSelectedFile}/>

                            <div>
                              csv must container a header row defining the attributes that will be imported.  app_name is the only required attribute for apps. server_name and app_id are required attributes for servers.
                              Any attributes defined in the csv that do not map to a configured application attributes will be ignored.
                            </div>
                          </div>
                        }

                        </div>
                        <hr />
                        {this.state.uploadRunning === 'complete' ?
                        <input
                          className="btn btn-primary btn-outline mt-3 mr-3 float-right"
                          type="button"
                          value="Close"
                          onClick={this.onClickCancelDialog}
                        />
                        :
                        <input
                          className="btn btn-primary btn-outline mt-3 mr-3 float-right"
                          disabled={this.state.uploadRunning === 'yes'}
                          type="button"
                          value={this.state.uploadRunning === 'yes'?"Uploading..":"Upload"}
                          onClick={this.onClickUpload}
                        />
                        }

                  </div>
                </div>
              </div>
            </div>
          </div>
        }

    </div>
    )
  }
}
