(()=>{
  const root=document.querySelector("[data-developer-api]");
  if(!root)return;

  const dialog=root.querySelector("dialog");
  const openers=document.querySelectorAll("[data-dev-open]");
  const close=root.querySelector("[data-dev-close]");
  const form=root.querySelector("form");
  const keyBox=root.querySelector("[data-dev-key]");
  const keyCode=root.querySelector("[data-dev-key-value]");
  const curl=root.querySelector("[data-dev-curl]");
  const error=root.querySelector("[data-dev-error]");
  const copy=root.querySelector("[data-dev-copy]");
  const run=root.querySelector("[data-dev-run]");
  const output=root.querySelector("[data-dev-output]");
  const outputStatus=root.querySelector("[data-dev-output-status]");
  const outputQuota=root.querySelector("[data-dev-output-quota]");
  const outputBody=root.querySelector("[data-dev-output-body]");
  const product=root.dataset.product;
  const endpoint=root.dataset.endpoint;
  const storage="developer-key:"+product;
  let activeKey="";
  let activePayload=null;

  const samplePayloads={
    "cold-clock":()=>{
      const suffix=Date.now().toString(36);
      return {
        data_use_acknowledgement:true,
        data_class:"synthetic",
        case_reference:`API trial ${suffix}`,
        contact_preference:"text",
        mobility_note:"Accessible delivery requested",
        medication:{display_name:"Example biologic",strength:"100 mg/mL",form:"prefilled pen",lot:`LOT-${suffix}`,opened_on:"2026-08-15"},
        package_transcription:`Example biologic\n100 mg/mL\nprefilled pen\nLOT-${suffix}`,
        label_source_title:"Synthetic authorized package insert",
        label_source_url:`https://example.test/label/${suffix}`,
        jurisdiction:"United States",
        quoted_storage_text:"Store between 36 and 46 degrees Fahrenheit.",
        monitoring_range_f:{minimum:36,maximum:46},
        baseline_fahrenheit:41,
        sensor_source:"Developer API synthetic sensor"
      };
    },
    "one-advisory":()=>{
      const suffix=Date.now().toString(36);
      return {
        synthetic_acknowledgement:true,
        data_class:"synthetic",
        advisory:{title:`North zone exercise ${suffix}`,authority:"Taylor Morgan, exercise commander - fictional",issued_at:"2026-08-17T10:00:00Z",zone_name:"North service zone - fictional",source_title:"Exercise advisory bulletin",source_url:`https://example.test/advisory/${suffix}`},
        facilities:[
          {type:"dialysis",name:"North Dialysis - fictional",contact:"Charge lead - fictional",capacity_note:"12 stations"},
          {type:"school_childcare",name:"North Learning Center - fictional",contact:"Site lead - fictional",capacity_note:"180 learners"},
          {type:"long_term_care",name:"North Care Home - fictional",contact:"Administrator - fictional",capacity_note:"64 residents"}
        ]
      };
    },
    "plan-kept":()=>{
      const suffix=Date.now().toString(36);
      const quote="Student A may request a quiet workspace during transitions.";
      return {
        synthetic_acknowledgement:true,
        data_class:"synthetic",
        case_reference:`Fictional support review ${suffix}`,
        student_reference:"Student A - fictional",
        plan_transcription:`FICTIONAL PLAN\n${quote}\nThis is not a real education record.`,
        promises:[{title:"Quiet workspace access",quote,category:"environment"}],
        participants:{student:"Student A - fictional",family:"Family participant - fictional",teacher:"Teacher participant - fictional",aide:"Support participant - fictional"}
      };
    }
  };

  function makePayload(){return samplePayloads[product]();}
  function makeCurl(key,payload){return `curl -X POST "${location.origin}${endpoint}" \\\n  -H "X-API-Key: ${key}" \\\n  -H "Content-Type: application/json" \\\n  --data '${JSON.stringify(payload)}'`;}
  function showKey(key){
    activeKey=key;
    activePayload=makePayload();
    keyBox.hidden=false;
    keyCode.textContent=key;
    curl.textContent=makeCurl(key,activePayload);
  }
  function showOutput(status,quota,data,isError=false){
    output.hidden=false;
    output.classList.toggle("is-error",isError);
    outputStatus.textContent=status;
    outputQuota.textContent=quota;
    outputBody.textContent=typeof data==="string"?data:JSON.stringify(data,null,2);
    output.scrollIntoView({block:"nearest",behavior:"smooth"});
  }

  openers.forEach(open=>open.addEventListener("click",event=>{
    event.preventDefault();
    dialog.showModal();
    const saved=sessionStorage.getItem(storage);
    if(saved)showKey(saved);
  }));
  close.onclick=()=>dialog.close();
  dialog.addEventListener("click",event=>{if(event.target===dialog)dialog.close();});

  form.onsubmit=async event=>{
    event.preventDefault();
    error.textContent="";
    const button=form.querySelector('button[type="submit"]');
    button.disabled=true;
    button.textContent="Generating...";
    try{
      const response=await fetch("/api/developer/keys",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({label:new FormData(form).get("label"),acceptable_use_acknowledgement:true})});
      const data=await response.json();
      if(!response.ok)throw new Error(data.detail||"Key generation failed");
      sessionStorage.setItem(storage,data.api_key);
      output.hidden=true;
      showKey(data.api_key);
    }catch(err){error.textContent=err.message;}
    finally{button.disabled=false;button.textContent="Generate free key";}
  };

  copy.onclick=async()=>{
    await navigator.clipboard.writeText(curl.textContent);
    copy.textContent="Copied";
    setTimeout(()=>copy.textContent="Copy curl",1300);
  };

  run.onclick=async()=>{
    if(!activeKey)return;
    run.disabled=true;
    run.textContent="Running real API...";
    showOutput("Request in progress","Connecting to durable workflow...","Waiting for the live service response.");
    try{
      const response=await fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json","X-API-Key":activeKey},body:JSON.stringify(activePayload)});
      const raw=await response.text();
      let data;
      try{data=JSON.parse(raw);}catch{data=raw||"No response body";}
      const remaining=response.headers.get("X-RateLimit-Remaining");
      const quota=remaining===null?"Quota header unavailable":`${remaining} calls remaining today`;
      showOutput(`${response.status} ${response.statusText}`.trim(),quota,data,!response.ok);
      if(!response.ok)throw new Error(typeof data?.detail==="string"?data.detail:"API request failed");
      activePayload=makePayload();
      curl.textContent=makeCurl(activeKey,activePayload);
    }catch(err){
      if(outputStatus.textContent==="Request in progress")showOutput("Request failed","No quota consumed",{error:err.message},true);
      error.textContent=err.message;
    }finally{
      run.disabled=false;
      run.textContent="Run live API test";
    }
  };
})();