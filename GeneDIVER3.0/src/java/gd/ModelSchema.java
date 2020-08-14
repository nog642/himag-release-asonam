package gd;

/*
 * Title: CProgram for reading a modeling schema
 *
 * @author               Gunjan Gupta
 * @version              1.0
 * @date                 December 16, 2002
 */

// Program for reading a schema used for reading
// schemas defined by matlab programs - the files
// with .sce extension can parse non string properties
// such as a string array of the form {'dfgsdfg', 'sdfgsdfg'}
// or a number array such as [20, 30.5]
// Implemented as a derivative of java property class

// Only one additional capability - can parse inputs
// which are really a string or a number array
// Returns an object which is either a string, an array
// of doubles, or an array of strings, which can be
// casted into the correct type for use by the user
// of this class

import java.util.Properties;
// import ModelUtil;

class ModelSchema extends Properties
{
   static final long serialVersionUID=32;
   // overload the get function to correctly parse the keys
   // returns null if not found a valid value - this function
   // should only be called to look up a double array or a string array
   // definition in the schema file, otherwise use getProperty only
   public Object getArrayProperty(String key)
   {
      Object value= get ((Object)key);
      if (value!= null)
      {
         try
         {
            Double dvalue= (Double) value;
         }
         catch (ClassCastException e)
         {
            String tempVal= (String) value;
            tempVal.trim();
            // check to see if its a string array definition ..
            if (tempVal.startsWith("{"))
            {
               value= ModelUtil.parseStringArray (tempVal);
            }
            else // or if its a number array definition
            if (tempVal.startsWith("["))
            {
               value= ModelUtil.parseNumberArray (tempVal);
            }
            else
            {
               value=null;
            }
         }
      }
      return value;
   }
};


